import cv2
import numpy as np

def convert_to_sat4(image_path):
    # Load the image
    image = cv2.imread(image_path)

    # Split the image into its color channels
    blue, green, red = cv2.split(image)

    # Calculate the NIR channel by subtracting the blue channel from the red channel
    nir = cv2.subtract(red, blue)

    # Merge the color channels and the NIR channel
    sat4 = cv2.merge([red, green, blue, nir])

    # Convert the image to uint8 data type (required by some machine learning libraries)
    sat4 = np.uint8(sat4)

    # Reshape the array to a single row and 3136 columns
    sat4_row = sat4.reshape(1, -1)

    return sat4_row

sat4_array = convert_to_sat4('snippet.png')
np.savetxt('sat4_image.csv', sat4_array, delimiter=',', fmt='%d')
