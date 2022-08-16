"""
A generalized approach to building Blurhashes, based on
https://github.com/halcy/blurhash-python (MIT license)

Goal:
    * Decouple the DCT, encoding, and "file format" steps
    * Make it easier to swap bases, use different packing, ...

TODO:
    * Most of this is only docstring sketches so far
    * Decoding is missing
"""

# Helper functions to select an appropriate quantizer and packer for a base

def get_quantizer(base):
    """Get the appropriate quantizer for this base. (Depending on the base,
    you will want different numbers of "steps" in your values.)"""
    if base==64:
        return base64quantizer
    else:
        raise NotImplementedError("Sorry, no quantizer for base %d yet" % base)


def get_packer(base):
    """Get the appropriate packer for this base. (This is where the actual
    data string format is constructed.)"""
    if base==64:
        return base64packer
    else:
        raise NotImplementedError("Sorry, no packer for base %d yet" % base)



# Actual base-specific quantizer and packer implementations

def base64quantizer(dc, ac_max, normalized_ac_components):
    """Map the various float values to suitable values usable in this base."""
    # return quant_dc, quant_ac_max, quant_components
    pass


def base64packer(components_x, components_y, dc, quant_ac_max, quant_ac_components):
    """Pack the quantized components into a string, using the digits
    of this base.
    TODO: Document the string format this packer is going to use."""
    # return packed_values
    pass



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
    Return the DC component, maximum AC component, and the normalized
    AC components."""
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
    return dc, max_ac_component, components



# Main function

def blurhash_encode(image, components_x, components_y, is_linear=True, base=83):
    """Put it all together"""
    if not is_linear:
        image = linearize(image)

    components = dct(image, components_x, components_y)

    dc, ac_max, normalized_ac_components = normalize(components)

    quantizer = get_quantizer(base)
    quant_dc, quant_ac_max, quant_components = quantizer(dc, ac_max, normalized_ac_components)

    packer = get_packer(base)
    packed_values = packer(components_x, components_y, dc, quant_ac_max,
            quant_ac_components)
    
    return packed_values

