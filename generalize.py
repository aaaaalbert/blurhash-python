"""
A generalized approach to building Blurhashes, based on
https://github.com/halcy/blurhash-python (MIT license)

Goal:
    * Decouple the DCT, encoding, and "file format" steps
    * Make it easier to swap bases, use different packing, ...

TODO:
    * All of this is completely untested
    * Decoding is missing
"""


# Actual base-specific quantizer and packer implementations

"""base64url format description:
* 4 channels (RGBA)
* 6-bit based encoding with URL-safe base64
* 4 base64 digits contain 24 bits, i.e. 3 bytes

Sequence of 6-bit fields:
--------- first byte
0   Escape  \x00    used because 0 is no meaningful size in default Blurhash
1   Type    \x17    arbitrary ID for this specific format
2   Size    3 bits for (x-1) and (y-1), each.
3   AC max
--------- second byte
4   DC components as RGBA-5658
5   (continued)
6   (continued)
7   (continued)
--------- third and further bytes
DCT components, 6 bits per channel

"""
def base64url_quantizer(dc, ac_max, normalized_ac_components):
    """Map the various float values to suitable values usable in this base."""
    height, width, number_of_channels = get_dimensions(normalized_ac_components)

    r, g, b, a = dc
    r = int(r * 31)
    g = int(g * 63)
    b = int(b * 31)
    a = int(a * 255)
    quant_dc = [r, g, b, a]

    quant_ac_max = ac_max * 63

    for y in range(height):
        for x in range(width):
            for c in range(number_of_channels):
                normalized_ac_components[y][x][c] *= 63

    return quant_dc, quant_ac_max, normalized_ac_components


def _base64url_word2bytes(word):
    """Convert 24-bit words to three-byte chunks."""
    # Mask out the three contained 8-bit sequences
    first = (word & 0xff00) >> 16
    second = (word & 0x00ff00) >> 8
    third = (word & 0x0000ff)
    return bytes(chr(first) + chr(second) + chr(third), "ASCII")


def base64url_packer(quant_dc, quant_ac_max, quant_ac_components):
    """Pack the quantized components into a string, using the digits
    of this base."""
    height, width, number_of_channels = get_dimensions(quant_ac_components)

    # Pack header
    first_word = ((((0b000000<<6 + 0b10111)<<6 + height-1)<<3 +
            width-1)<<3 + quant_ac_max)

    r, g, b, a = quant_dc
    second_word = ((r<<6 + g)<<5 + b)<<8 + a

    header_bytes = (_base64url_word2bytes(first_word) +
            _base64url_word2bytes(second_word))

    packed_values = base64.b64encode(header_bytes, altchars=b"-_")

    # Pack DCT AC components
    pixel_bytes = b""
    for y in range(height):
        for x in range(width):
            pixel_word = 0
            for c in range(number_of_channels):
                pixel_word = pixel_word << 6 + quant_ac_components[y][x][c]
            current_pixel_bytes = _base64url_word2bytes(pixel_word)
            pixel_bytes += base64.b64encode(current_pixel_bytes)

    packed_values += pixel_bytes

    return packed_values



# Helper functions needed for building the Blurhash components

def srgb_to_linear(value):
    """
    Convert sRGB value (integer, 0-255) to linear (float, 0.0-1.0).
    (value must be in correct range, we don't check.)
    See https://en.wikipedia.org/wiki/SRGB#Transformation for details
    """
    value = value / 255
    if value <= 0.04045:
        return value / 12.92
    else:
        return math.pow((value + 0.055) / 1.055, 2.4)


def linear_to_srgb(value):
    """
    Convert linear value (float, 0.0-1.0) to sRGB (integer, 0-255)
    (value must be in correct range, we don't check.)
    See https://en.wikipedia.org/wiki/SRGB#Transformation for details
    """
    if value <= 0.0031308:
        return int(value * 12.92 * 255 + 0.5)
    else:
        return int((1.055 * math.pow(value, 1 / 2.4) - 0.055) * 255 + 0.5)


def sign_pow(value, exp):
    """
    Sign-preserving exponentiation.
    """
    return math.copysign(math.pow(abs(value), exp), value)


def linearize(image):
    """Convert image from sRGB to linear.
    Return linearized image."""
    pass


def get_dimensions(image):
    height = len(image)
    width = len(image[0])
    number_of_channels = len(image[0][0])
    return height, width, number_of_channels


def dct(image, components_x, components_y):
    """Perform the Discrete Cosine Transform on the image.
    Return the 2D list of components (x and y dimensions),
    each containing as many entries as the image has channels."""
    height, width, number_of_channels = get_dimensions(image)

    # Calculate components
    components = []
    for j in range(components_y):
        for i in range(components_x):
            if i==j==0:
                norm_factor = 1.0
            else:
                norm_factor = 2.0
            component = []
            for y in range(int(height)):
                for x in range(int(width)):
                    basis = norm_factor * math.cos(math.pi * i * x / width) * \
                                          math.cos(math.pi * j * y / height)
                    for c in range(number_of_channels):
                        component[c] += basis * image[y][x][c]

            for c in range(number_of_channels):
                component[c] /= (width * height)
            components.append(component)

    return components



def normalize(components):
    """Normalize the AC components of the DCT.
    Return the maximum AC component and the normalized AC components.
    (The DC component is left unchanged.)"""
    height, width, number_of_channels = get_dimensions(components)

    dc = components[0][0]
    max_ac_component = 0
    for channel in range(number_of_channels):
        # XXX No `abs` for lists?
        potential_max = max(components[1:][channel])
        potential_min = min(components[1:][channel])
        max_ac_component = max(max_ac_component, potential_max, -potential_min)

    # Normalize every AC component. (DC is at index 0, we'll restore it later.)
    for y in range(0, height):
        component = []
        for x in range(0, width):
            for c in range(number_of_channels):
                components[y][x][c] /= max_ac_component

    components[0][0] = dc
    return max_ac_component, components



# Main function

def blurhash_encode(image, components_x, components_y, is_linear=True, base=83):
    """Put it all together"""
    if not is_linear:
        image = linearize(image)

    components = dct(image, components_x, components_y)

    dc = components[0][0]
    ac_max, normalized_ac_components = normalize(components)

    quant_dc, quant_ac_max, quant_components = quantizer[base](dc, ac_max, normalized_ac_components)

    packed_values = packer[base](components_x, components_y, dc, quant_ac_max,
            quant_ac_components)
    
    return packed_values



# Helper dicts to store quantizer and packer functions for a named base
#
# Add yours here (plus a short note to describe them)

quantizer = {
        # Base64-URL, https://datatracker.ietf.org/doc/html/rfc4648#section-5
        # (like Python's base64.b64encode with altchars="-_" and no padding)
        "base64-url": base64url_quantizer,
        }

packer = {
        # XXX Uses a slightly alternative 4-channel format for now
        "base64-url": base64url_packer,
        }

