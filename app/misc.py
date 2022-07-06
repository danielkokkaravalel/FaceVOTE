import zlib
from base64 import b64encode, b64decode


def writeImg(encoded_image):
    compressed_data = zlib.compress(encoded_image, 9)
    uncompressed_data = zlib.decompress(compressed_data)
    decoded_data = b64decode(uncompressed_data)
    return decoded_data
