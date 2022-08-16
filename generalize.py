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

def linearize(image):
    """Convert image from sRGB to linear.
    Return linearized image."""
    pass


def dct(image, components_x, components_y):
    """Perform the Discrete Cosine Transform on the image.
    Return the 2D list of components (x and y dimensions),
    each containing as many entries as the image has channels."""
    pass


def normalize(components):
    """Normalize the AC components of the DCT.
    Return the DC component, maximum AC component, and the normalized
    AC components."""
    pass



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

