import numpy as np
from skimage.io import imshow
import matplotlib.pyplot as plt
from tensorflow import keras

# Load the saved model
model = keras.models.load_model('./model')

# Load and preprocess the input image
X_test_img = np.genfromtxt('./input/sat4_image.csv', delimiter=',').reshape(28, 28, 4) / 255
X_test = np.expand_dims(X_test_img, axis=0)

# Make predictions
preds = model.predict(X_test, verbose=1)

# Visualize the input image
imshow(X_test_img[:, :, :3].astype(float) * 255)
plt.show()

# Print the predicted class probabilities and the ground truth label
print('Prediction:\n{:.1f}% probability barren land,\n{:.1f}% probability trees,\n{:.1f}% probability grassland,\n{:.1f}% probability other\n'.format(preds[0,0]*100,preds[0,1]*100,preds[0,2]*100,preds[0,3]*100))