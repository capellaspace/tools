# Produces a float32 amplitude image from a Capella Single Look Complex (SLC) product
#
# Copyright: Capella Space Corp. 2019
#


import gdal
import os
import json
import numpy as np


def amplitude_image(input_file_path, output_file_path, meta_path=None):
    driver = gdal.GetDriverByName('GTiff')

    input_ds = gdal.Open(input_file_path)

    output_ds = driver.Create(output_file_path, input_ds.RasterXSize, input_ds.RasterYSize, input_ds.RasterCount,
                              gdal.GDT_Float32)

    projection = input_ds.GetProjection()
    output_ds.SetProjection(projection)

    geotransform = input_ds.GetGeoTransform()
    output_ds.SetGeoTransform(geotransform)

    gcps = input_ds.GetGCPs()
    output_ds.SetGCPs(gcps, projection)

    meta = json.loads(input_ds.GetMetadataItem("TIFFTAG_IMAGEDESCRIPTION"))
    scale = meta["collect"]["image"]["scale_factor"]
    slc_image = input_ds.GetRasterBand(1).ReadAsArray()
    output_ds.GetRasterBand(1).WriteArray(np.abs(slc_image * scale))
    
    meta_dict = input_ds.GetMetadata_Dict()
    output_ds.GetRasterBand(1).SetMetadata(meta_dict)

    input_ds = None
    output_ds = None


def batch_amplitude_image(input_directory, suffix):

    tiff_files = [os.path.join(input_directory, f) for f in os.listdir(input_directory) if f.endswith(".tif") and not
                  f.endswith("_grid.tif")]
    output_files = [os.path.join(input_directory, os.path.splitext(os.path.basename(f))[0] + suffix + ".tif") for f in
                    tiff_files]

    for tiff_file, output_file in zip(tiff_files, output_files):
        amplitude_image(tiff_file, output_file)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Produces float32 amplitude images from Capella Single Look Complex "
                                                 "(SLC) products)")

    subparsers = parser.add_subparsers(help="Process all files in a directory", dest='command')

    single = subparsers.add_parser("single", help="Produce a single amplitude image")
    single.add_argument("input_file_path", type=str, help="The path to the input TIFF file from the SLC product")
    single.add_argument("output_file_path", type=str, help="The path to write the output TIFF file to")

    batch = subparsers.add_parser("batch", help="Produces amplitude images of all products in the given directory")
    batch.add_argument("input_path", help="The path to the directory of products")
    batch.add_argument("suffix", help="The suffix to be appended to each input file name to create its output file "
                       "name")

    args = parser.parse_args()

    if args.command == "single":
        amplitude_image(args.input_file_path, args.output_file_path)
    elif args.command == "batch":
        batch_amplitude_image(args.input_path, args.suffix)


if __name__ == '__main__':
    main()
