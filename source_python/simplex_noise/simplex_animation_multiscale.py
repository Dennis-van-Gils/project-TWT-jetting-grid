#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from matplotlib import pyplot as plt
from matplotlib import animation
import numpy as np
import opensimplex


def create_simplex_img_stack(N_frames_, N_pixels_, end_time_, px_max_):
    px_x = np.linspace(0, px_max_, N_pixels_, endpoint=False)
    px_y = np.linspace(0, px_max_, N_pixels_, endpoint=False)
    time = np.linspace(0, end_time_, N_frames_, endpoint=False)
    return opensimplex.noise3array(px_x, px_y, time)


opensimplex.seed(1)
N_pixels = 1000  # Number of pixels on a single axis
N_frames = 200  # Number of time frames

print("Generating noise...", end="")

# Generate large-scale noise
img_stack_LS = create_simplex_img_stack(
    N_frames_=N_frames, N_pixels_=N_pixels, end_time_=10, px_max_=5
)

# Generate small-scale noise
img_stack_SS = create_simplex_img_stack(
    N_frames_=N_frames, N_pixels_=N_pixels, end_time_=10, px_max_=20
)

# Mix small-scale and large-scale noise together and rescale
img_stack = np.empty((N_frames, N_pixels, N_pixels), dtype=int)
img_stack_BW = np.zeros((N_frames, N_pixels, N_pixels), dtype=int)
alpha = np.zeros(N_frames)  # Grid transparency
for idx_frame, img in enumerate(img_stack_SS):
    # Mix
    np.add(img, img_stack_LS[idx_frame], out=img)
    np.divide(img, 2, out=img)

    # Calculate grid transparency
    alpha[idx_frame] = np.sum(img > 0) / N_pixels / N_pixels

    # Rescale noise from [-1, 1] to [0, 255]
    np.add(img, 1, out=img)
    np.multiply(img, 128, out=img)
    img = img.astype(int)

    img_stack[idx_frame] = img
    img_stack_BW[idx_frame][np.where(img > 128)] = 255

print(" done.")

fig = plt.figure()
ax = plt.axes()
img = plt.imshow(img_stack[0], cmap="gray", interpolation="none")
frame_text = ax.text(0, 1.02, "", transform=ax.transAxes)


def init_anim():
    img.set_data(img_stack[0])
    frame_text.set_text("")
    return img, frame_text


def anim(i):
    img.set_data(img_stack[i])
    frame_text.set_text("frame %03d, transparency = %.2f" % (i, alpha[i]))
    return img, frame_text


ani = animation.FuncAnimation(
    fig, anim, frames=N_frames, interval=40, init_func=init_anim  # blit=True,
)

plt.grid(False)
plt.axis("off")
plt.show()

fig2 = plt.figure(2)
ax2 = plt.plot(alpha)
plt.xlim(0, N_frames)
plt.title("transparency")
plt.xlabel("frame #")
plt.ylabel("alpha [0 - 1]")
plt.show()
