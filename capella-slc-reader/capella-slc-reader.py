# Single Look Complex (SLC) Reader for Capella Space SAR data
#
# Copyright: Capella Space Corp. 2019
# Author:    Jordan Heemskerk
#
#
# Usage:
#       $ python SLC_reader.py <file-in> <file-out>


import sys
import gdal
import numpy as np

def main():

    # input SLC geotiff filename from command line
    # generate Amplitude geotiff output file

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        mode = sys.argv[3]
    except IndexError:
        mode = None

    driver = gdal.GetDriverByName('GTiff')

    input_ds = gdal.Open(input_file)

    gcps = input_ds.GetGCPs()
    output_ds = driver.Create(output_file, input_ds.RasterXSize, input_ds.RasterYSize, input_ds.RasterCount,
                              gdal.GDT_Float32)
    output_ds.SetGCPs(gcps, input_ds.GetProjection())

    block_size = 10000

    for line_number in range(0, input_ds.RasterYSize, block_size):
        print(line_number)
        block_size = min(block_size, input_ds.RasterYSize - line_number)
        for band_number in range(1, input_ds.RasterCount + 1):
            block_data = input_ds.GetRasterBand(band_number).ReadAsArray(yoff=line_number, win_ysize=block_size)

            # For each block of data Real and Imaginary components are extracted.
            # The datatype of SLC GeoTIFF files is CInt16. The CInt16 dataype has 32 bits for each sample. The first 16 bits represent 
            # the real component of the complex value as a signed 16 bit integer (Int16) and the last 16 bits represent the imaginary 
            # component of the complex value as a signed 16 bit integer (Int16).

            if mode == 'int16':
                interleaved_datatype = np.dtype((np.int32,  {'i': (np.int16, 0), "j": (np.int16, 2)}))
                block_data_view = block_data.view(dtype=interleaved_datatype)

                # Compute the squared of SLC complex values = (Re + j*Im)^2

                detected_block_data = np.abs(block_data_view['i'].astype(np.float32) + 1j *
                                             block_data_view['j'].astype(np.float32)) ** 2

                # From Linear to dB

                log_detected_block_data = 10 * np.log10(detected_block_data)
                log_detected_block_data[detected_block_data == 0] = 0
                detected_block_data = log_detected_block_data

            else:
                detected_block_data = np.abs(block_data) ** 2

            # write output   
            output_ds.GetRasterBand(band_number).WriteArray(detected_block_data.astype(np.float32), yoff=line_number)

    input_ds = None
    output_ds = None

    print("Done")

if __name__ == '__main__':
    main()
