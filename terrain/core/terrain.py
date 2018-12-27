import warnings
from math import pi

import numpy as np
from scipy import ndimage


def _ring_gradient(arr, step=(1, 1)):
    """Convolve an array using a 3x3 ring-shaped kernel

    Parameters:
        arr (ndarray): 2D numpy array
        step (tuple): tuple of raster cell width and height

    Returns:
        dz_dx, dz_dy (ndarrays): x and y gradient components

    """
    origin = (0, 0)

    k_X = np.array([[-1, 0, 1],
                    [-2, 0, 2],
                    [-1, 0, 1]])
    k_Y = np.array([[-1, -2, -1],
                    [0, 0, 0],
                    [1, 2, 1]])

    dz_dx = ndimage.convolve(arr, k_X, origin=origin) / (8 * step[0])
    dz_dy = ndimage.convolve(arr, k_Y, origin=origin) / (8 * step[1])

    return dz_dx, dz_dy


def slope(arr, step=(1, 1), units='grade', neighbors=4):
    """Calculates slope.

    Parameters:
        arr (ndarray): 2D numpy array
        step (tuple): tuple of raster cell width and height
        units (str, optional): choice of grade or degrees
        neighbors (int, optional): use four or eight neighbors in calculation

    Returns:
        slope (ndarray): 2D numpy array representing slope

    """
    if neighbors == 4:
        dz_dx, dz_dy = np.gradient(arr, step[0])
    else:
        dz_dx, dz_dy = _ring_gradient(arr, step)

    m = np.sqrt(dz_dx**2 + dz_dy**2)
    if units == 'grade':
        slope = m
    elif units == 'degrees':
        slope = (180/pi) * np.arctan(m)

    return slope


def aspect(arr, step=(1, 1), pcs='compass', neighbors=4):
    """Calculates aspect.

    Parameters:
        arr (ndarray): 2D numpy array
        step (tuple): tuple of raster cell width and height
        north (str, optional): choice of polar coordinate systeM

    Returns:
        aspect (ndarray): 2D numpy array representing slope aspect

    """
    if neighbors == 4:
        dz_dx, dz_dy = np.gradient(arr, step[0])
    else:
        dz_dx, dz_dy = _ring_gradient(arr, step)

    if pcs == 'compass':
        aspect = (180/pi)*np.arctan2(dz_dy, -dz_dx)
        aspect += 180
    elif pcs == 'cartesian':
        aspect = (180/pi)*np.arctan2(-dz_dy, dz_dx)
        aspect = 90.0 - aspect
        aspect[aspect < 0] += 360
    else:
        aspect = (180/pi)*np.arctan2(dz_dy, dz_dx)

    return aspect


def curvature(arr, step=(1, 1), neighbors=4):
    """Calculates curvature.

    Parameters:
        arr (ndarray): 2D numpy array
        step (tuple): tuple of raster cell width and height

    Returns:
        curvature (ndarray): 2D numpy array representing surface curvature

    """
    if neighbors == 4:
        dz_dx, dz_dy = np.gradient(arr, step[0])
    else:
        dz_dx, dz_dy = _ring_gradient(arr, step)

    m = np.sqrt(dz_dx**2 + dz_dy**2)
    dT_dx = np.divide(dz_dx, m)
    dT_dy = np.divide(dz_dy, m)
    d2T_dxx, _ = np.gradient(dT_dx, step[0])
    _, d2T_dyy = np.gradient(dT_dy, step[0])

    curvature = d2T_dxx + d2T_dyy

    return curvature
