import ee
import requests
from PIL import Image

# Initialize the Earth Engine API
ee.Initialize()

# Define the coordinates and altitude of the satellite image
lat = 51.44634
lon = -57.8088
alt = 5000  # in meters

# Create a geometry object from the coordinates
point = ee.Geometry.Point(lon, lat)

# Create an image collection object of Sentinel-2 surface reflectance data
collection = ee.ImageCollection('COPERNICUS/S2_SR')

# Filter the collection to get only images acquired during daytime
collection = collection.filter(ee.Filter.calendarRange(10, 18, 'hour'))

# Filter the collection to get a single image at the given point and altitude
image = collection.filterBounds(point).filterMetadata('CLOUDY_PIXEL_PERCENTAGE', 'less_than', 10).sort('CLOUDY_PIXEL_PERCENTAGE').first().resample('bicubic').reproject(crs='EPSG:4326', scale=10).clip(point.buffer(alt).bounds().buffer(10000))

# Get the URL of the image
url = image.getThumbUrl({
    'min': 0,
    'max': 3000,
    'dimensions': '350',
    'region': point.buffer(alt).bounds().getInfo()['coordinates']
})

# Download the image and save it locally
response = requests.get(url)
with open('satellite_image.jpg', 'wb') as f:
    f.write(response.content)

# Open the image using PIL
img = Image.open('satellite_image.jpg')
img.show()
