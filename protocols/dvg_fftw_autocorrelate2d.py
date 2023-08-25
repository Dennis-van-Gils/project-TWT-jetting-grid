#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Performs lightning-fast autocorrelation on 2D input arrays.

The correlation is based on the fast-Fourier transform (FFT) as performed by the
excellent `fftw` (http://www.fftw.org) library. It will plan the transformations
ahead of time to optimize the calculations. Also, multiple threads can be
specified for the FFT and, when set to > 1, the Python GIL will not be invoked.
This results in true multithreading across multiple cores, which can result in a
huge performance gain.

NOTE: This algorithm produces slightly different results from
`scipy.signal.correlate()`. See the demo when run as main.
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/2D-PIV-BOS"
__date__ = "25-08-2023"
__version__ = "1.0.0"
# pylint: disable=invalid-name, missing-function-docstring

import sys
import numpy as np
import numpy.typing as npt
import pyfftw
from numba import njit, prange

# ------------------------------------------------------------------------------
#   fast_multiply
# ------------------------------------------------------------------------------

"""Timeit results on computer Onera:

                [ms] per iter
shape           fast_multiply   fast_multiply_p
(32, 32)        --> 0.00102         0.01334
(64, 64)        --> 0.00222         0.01491
(128, 128)      --> 0.00718         0.02000
(256, 256)      --> 0.02753         0.03023
(512, 512)          0.10537     --> 0.06094
(1024, 1024)        0.78878     --> 0.40209
(2048, 2048)        4.00985     --> 3.85964
"""


@njit(
    nogil=True,
    cache=True,
)  # TODO: timeit to potentially speed up code even more. Add numba signatures
def fast_conjugate(in1):
    return np.conjugate(in1)


@njit(
    "(complex64[:, ::1], complex64[:, ::1], complex64[:, ::1])",
    nogil=True,
    cache=True,
)
def fast_multiply(
    in1: npt.NDArray[np.complex64],
    in2: npt.NDArray[np.complex64],
    out: npt.NDArray[np.complex64],
):
    """
    * In-place operation on `out`.
    * Faster version of `out = np.multiply(in1, in2)`.
    * Not parallelized.
    """
    for i in range(in1.shape[0]):
        for j in range(in1.shape[1]):
            out[i, j] = in1[i, j] * in2[i, j]


@njit(
    "(complex64[:, ::1], complex64[:, ::1], complex64[:, ::1])",
    nogil=True,
    cache=True,
    parallel=True,
)
def fast_multiply_p(
    in1: npt.NDArray[np.complex64],
    in2: npt.NDArray[np.complex64],
    out: npt.NDArray[np.complex64],
):
    """
    * In-place operation on `out`.
    * Faster version of `out = np.multiply(in1, in2)`.
    * Parallelized. Only beneficial for `shape >~ (256, 256)`. Use
    `fast_multiply_o()` when shape is smaller.
    """
    for i in prange(in1.shape[0]):
        for j in prange(in1.shape[1]):
            out[i, j] = in1[i, j] * in2[i, j]


@njit(
    nogil=True,
    cache=True,
)
def fast_fftshift(C):
    """Like `numpy.fft.fftshift(), but faster."""
    rows, cols = C.shape
    half_rows = rows // 2
    half_cols = cols // 2

    # Swap quadrants
    shifted = np.empty_like(C)
    shifted[:half_rows, :half_cols] = C[half_rows:, half_cols:]
    shifted[:half_rows, half_cols:] = C[half_rows:, :half_cols]
    shifted[half_rows:, :half_cols] = C[:half_rows, half_cols:]
    shifted[half_rows:, half_cols:] = C[:half_rows, :half_cols]

    return shifted


# ------------------------------------------------------------------------------
#   FFTW_Autocorrelator_2D
# ------------------------------------------------------------------------------


class FFTW_Autocorrelator_2D:
    """Manages a fast-Fourier transform (FFT) autocorrelation on 2D input array
    `in1` as passed to method `autocorrate()`, which will return the
    result as a `numpy.ndarray` containing the 'full' convolution elements.

    Args:
        s1 (tuple):
            Shape of the upcoming input array `in1` passed to method
            `convolve()`.

        fftw_threads (int, optional):
            Number of threads to use for the FFT transformations. When set to
            > 1, the Python GIL will not be invoked.

            Default: 5
    """

    def __init__(self, s1: tuple, fftw_threads: int = 5):
        axes = (0, 1)

        # Speed up FFT by padding to optimal size.
        self.fshape = [pyfftw.next_fast_len(s1[a]) for a in axes]
        fshape_out = [self.fshape[0], self.fshape[1] // 2 + 1]

        # Slice corresponding to the 'full' convolution elements to be
        # finally returned as convolution result
        self.fslice = tuple([slice(sz) for sz in s1])

        # Create the FFTW plans
        # fmt: off
        self._rfft_in   = pyfftw.zeros_aligned(self.fshape, dtype="float32")
        self._rfft_out  = pyfftw.empty_aligned(fshape_out , dtype="complex64")
        self._irfft_in  = pyfftw.empty_aligned(fshape_out , dtype="complex64")
        self._irfft_out = pyfftw.empty_aligned(self.fshape, dtype="float32")
        # fmt: on

        print("Creating FFTW plans for convolution...", end="")
        sys.stdout.flush()

        p = {
            "axes": (0, 1),
            "flags": ("FFTW_MEASURE", "FFTW_DESTROY_INPUT"),
            "threads": fftw_threads,
        }
        self._fftw_rfft = pyfftw.FFTW(self._rfft_in, self._rfft_out, **p)
        self._fftw_irfft = pyfftw.FFTW(
            self._irfft_in,
            self._irfft_out,
            direction="FFTW_BACKWARD",
            **p,
        )

        print(" done.")

    # --------------------------------------------------------------------------
    #   autocorrelate
    # --------------------------------------------------------------------------

    def autocorrelate(
        self, in1: npt.NDArray[np.float32]
    ) -> npt.NDArray[np.float32]:
        """Performs the FFT autocorrelation on input array `in1` and
        returns the result as a `numpy.ndarray`.

        Returns:
            The autocorrelation results as a 2D numpy array with a shape
            equal to `in1`.

        NOTE: `in1` does not necessarily have to be C-contiguous,
        because they will, internal to this method, get copied into C-contiguous
        arrays during the zero-padding operation.
        NOTE: The output matrix is not contiguous.
        """

        # Zero padding and forwards Fourier transformation
        self._rfft_in[: in1.shape[0], : in1.shape[1]] = in1
        self._fftw_rfft()

        fast_multiply(
            self._rfft_out, fast_conjugate(self._rfft_out), self._irfft_in
        )

        # Backwards Fourier transformation
        result = self._fftw_irfft()

        # Return the results
        return fast_fftshift(result[self.fslice] / (in1.size))


# --------------------------------------------------------------------------
#   main
# --------------------------------------------------------------------------

if __name__ == "__main__":
    import timeit
    import scipy.signal
    import matplotlib.pyplot as plt

    def gaussian_kernel(n, std1, std2):
        gaussian1D_1 = scipy.signal.windows.gaussian(n, std1)
        gaussian1D_2 = scipy.signal.windows.gaussian(n, std2)
        gaussian2D = np.outer(gaussian1D_1, gaussian1D_2)
        return gaussian2D

    # Create interesting test image to autocorrelate
    size_A = 512
    N_squares = 6
    A = gaussian_kernel(size_A, size_A / 8, size_A / 4) * 0.75
    for i in range(N_squares):
        px = int((i + 1) * size_A / (N_squares + 1))
        A[px - 20 : px + 20, 200:220] = 1
        A[px - 20 : px + 20, 292:312] = 1

    # Autocorrelate
    fftw_1 = FFTW_Autocorrelator_2D(A.shape, fftw_threads=4)
    Cxx = fftw_1.autocorrelate(A)

    # Again, with scipy. To compare.
    mode = "same"
    Cxx_scipy = scipy.signal.correlate(A, A, mode=mode, method="auto")
    Cxx_scipy = Cxx_scipy / A.size

    # Plot
    fig, axs = plt.subplots(nrows=1, ncols=3, figsize=(12, 4))
    p = {"cmap": "cool", "interpolation": "none"}

    axs[0].imshow(A, **p)
    axs[0].title.set_text("Test image")

    axs[1].imshow(Cxx, **p)
    axs[1].title.set_text("FFTW_Autocorrelator_2D")

    axs[2].imshow(Cxx_scipy, **p)
    axs[2].title.set_text("scipy.signal.correlate")
    if mode == "full":
        axs[2].set_xlim([255, 768])
        axs[2].set_ylim([255, 768])

    plt.show()

    # Timeit
    loop = 100
    result = timeit.timeit(
        "fftw_1.autocorrelate(A)",
        setup=lambda: fftw_1.autocorrelate(A),
        globals=globals(),
        number=loop,
    )
    result = result / loop * 1000
    print(f"FFTW_Autocorrelator_2D, [ms] per iter: {result:.3f}")

    result = timeit.timeit(
        "scipy.signal.correlate(A, A, mode=mode, method='auto')",
        setup=lambda: scipy.signal.correlate(A, A, mode=mode, method="auto"),
        globals=globals(),
        number=loop,
    )
    result = result / loop * 1000
    print(f"scipy.signal.correlate, [ms] per iter: {result:.3f}")
