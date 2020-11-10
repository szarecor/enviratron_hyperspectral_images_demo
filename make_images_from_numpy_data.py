"""
Minimal Python Version: 3.6

This is pipeline code around generating the most legible image from hyperspectral source data.

Choosing the band with the median standard deviation gives us the best "exposure" when generating images

TODO: Some bands of some source files produce images with vertical seams/lines. After some exploration, I believe
this comes from the source data. But, that needs to be confirmed. Also, code should be written to try to detect those
bands with numpy and avoid using a band with these seams to generate images.
"""

import os
from pathlib import Path
import numpy as np
import cv2
import matplotlib.pyplot as plt
from matplotlib import cm
import PIL
from enviratron_filename_parser import EnviratronFileNameParser


def get_mpl_colormap(cmap_name="gray"):
    """ Gets a matplotlib.colormap instance from a string name """
    cmap = cm.get_cmap(cmap_name)
    sm = plt.cm.ScalarMappable(cmap=cmap)
    # Obtain linear color range
    color_range = sm.to_rgba(np.linspace(0, 1, 256), bytes=True)[:, 2::-1]
    return color_range.reshape(256, 1, 3)


def load_hyperspectral_numpy_data(path):
    """ Loads a numpy file, reshapes it based on the dimensions found in the filename from the given path and returns the data """
    BAND_COUNT = 56

    image_data = np.load(path)
    input_meta = EnviratronFileNameParser(path)
    width = input_meta.width
    height = input_meta.height
    # Two dim matrix with each row representing all the datapoints/pixels for a particular wavelength/band:
    image_data = np.reshape(image_data, (BAND_COUNT, height * width))
    return image_data


def apply_colormap(image_data, colormap_name="gray"):
    """ Takes image data in the form of a numpy vector and applies a matplotlib.colormap and returns the colormapped data"""
    color_map = get_mpl_colormap(colormap_name)
    mapped_image = cv2.applyColorMap(np.uint8(image_data), color_map)
    return mapped_image


def _log(*argv):
    print(*argv)

def main(input_dir, output_dir, overwrite_existing=False, verbose=True):
    """ Processes the numpy files in input_dir and generates images from the data therein """
    for root, subdirs, filenames in os.walk(input_dir):

        for filename in filenames:
            meta_data = EnviratronFileNameParser(filename)
            # Base all the output filenames on the input filenames:
            base_output_filename = filename.rstrip(".npy")

            # Reconstruct the directory structure of the input data for the output data:
            output_dir_structure = root.replace(input_dir, output_dir)
            Path(output_dir_structure).mkdir(parents=True, exist_ok=True)


            median_output_filename = f"{base_output_filename}.png"
            image_exists = os.path.exists(f"{output_dir_structure}/{median_output_filename}")

            # If a particular file has already been processed and the overwrite_existing param is False, skip processing:
            if image_exists and not overwrite_existing:
                if verbose:
                    _log(f"SKIPPING:\t", meta_data.raw_filename)
                continue

            # The data grouped by bands
            # Should have shape: rows == bands and width == image.height * image.width
            data_by_band = load_hyperspectral_numpy_data(f"{root}/{filename}")

            # Identify the bands with the median standard deviation:
            std_deviation = np.std(data_by_band, axis=1)


            median_std_deviation_index = np.argsort(std_deviation)[
                len(std_deviation) // 2
            ]

            # There's metadata stored in the source filenames (date, width, height, etc),
            # EnviratronFileNameParser is a helper for extracting that data:
            image_size = (meta_data.height, meta_data.width)

            if verbose:
                _log(f"WRITING {output_dir_structure}/{base_output_filename} FILE. BAND INDEX: {median_std_deviation_index}")


            # Write the image for the band with the median standard deviation:
            median_band_data = data_by_band[median_std_deviation_index] * 255
            median_band_data = np.reshape(median_band_data, image_size)
            median_image_data = apply_colormap(median_band_data, "gray")

            # Use PIL instead of cv2 to write the image for excellent file size optimization:
            output_image = PIL.Image.fromarray(median_image_data, "RGB")
            output_image.save(
                f"{output_dir_structure}/{median_output_filename}", optimize=True
            )


if __name__ == "__main__":

    import sys

    # This probably doesn't execute with python 2.x because the interpreter will throw errors first:
    if sys.version_info < (3, 6):
        raise RuntimeError("This file requires Python 3.6+")

    INPUT_ROOT = "/home/scott/virtualenvs/enviratron-imaging/code2/numpy_data/c1_2019_5_27_7_6_50_692/"
    OUTPUT_ROOT = "/home/scott/virtualenvs/enviratron-imaging/code2/hs_images/"

    main(INPUT_ROOT, OUTPUT_ROOT)
