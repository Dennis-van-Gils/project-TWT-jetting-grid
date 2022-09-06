#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from matplotlib import pyplot as plt
from matplotlib import animation
import numpy as np
import opensimplex

opensimplex.seed(1)

numel_axis = 1000
px_x = np.linspace(0, 10, numel_axis)
px_y = np.linspace(0, 10, numel_axis)
time = np.arange(0, 10, 0.05)

img_stack = opensimplex.noise3array(px_x, px_y, time)
for idx_frame, img in enumerate(img_stack):
    # Rescale noise from [-1, 1] to [0, 255]
    img = np.multiply(img + 1, 128).astype(int)
    img_stack[idx_frame] = img


fig = plt.figure()
ax = plt.axes(xlim=(0, px_x.size), ylim=(0, px_y.size))
img = plt.imshow(img_stack[0], cmap="gray", interpolation="none")
frame_text = ax.text(0, 1.02, "", transform=ax.transAxes)


def init_anim():
    img.set_data(img_stack[0])
    frame_text.set_text("")
    return img, frame_text


def anim(i):
    img.set_data(img_stack[i])
    frame_text.set_text("frame %d" % i)
    return img, frame_text


ani = animation.FuncAnimation(
    fig, anim, frames=time.size, interval=20, init_func=init_anim  # blit=True,
)

plt.grid(False)
plt.axis("off")
plt.show()
