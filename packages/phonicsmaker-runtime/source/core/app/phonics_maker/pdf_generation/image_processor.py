import cv2
import numpy as np
from skimage import measure
import os
from sklearn.cluster import KMeans
import requests
from urllib.parse import urlparse
from typing import List, Set
import re
import os
import colorsys
import unicodedata
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from app.core.config.logger import logger
from app.core.utils.retry import retry
from app.core.config.config import settings


PHONEME_REGEX_PATTERNS = {
    # ══════════════════════════════════════════════════════════════════
    # ENGLISH PHONEME PATTERNS
    # ══════════════════════════════════════════════════════════════════

    # Consonant Digraphs
    'SH': r'sh',
    'TH': r'th',
    'CH': r'ch(?![aeiou]r)',  # Standard CH sound, not like in character
    'WH': r'wh',
    'PH (f sound)': r'ph',

    # Long Vowel Combinations
    'EE': r'ee',
    'EA (eat)': r'ea(?![ru])',  # EA as in eat, not as in bear or beauty
    'AI': r'ai',
    'AY': r'ay',
    'OA': r'oa',
    'OW (slow)': r'ow(?![nl])',  # OW as in slow, not as in down or owl
    'IGH': r'igh',
    'IGN': r'ign',
    'ING': r'ing',

    # OO Sounds
    'OO (zoom)': r'oo(?![dk])',  # OO as in zoom, not as in book or blood
    'OO (book)': r'oo[dk]',  # OO as in book or look

    # Diphthongs
    'OU': r'ou(?!gh|r)',  # OU not followed by gh or r
    'OW (cow)': r'ow(?=[nl])',  # OW as in down or owl
    'OI': r'oi',
    'OY': r'oy',
    'AU': r'au(?!gh)',  # AU not in augh
    'AW': r'aw',
    'EW': r'ew',

    # R-Controlled Vowels
    'AR': r'ar(?!$)',  # AR not at end of word
    'ER': r'er',
    'IR': r'ir',
    'OR': r'or(?!$)',  # OR not at end of word
    'UR': r'ur',

    # Silent E Patterns (uppercase key form)
    'A-E': r'a[^aeiou]e(?=$|\s)',
    'E-E': r'e[^aeiou]e(?=$|\s)',
    'I-E': r'i[^aeiou]e(?=$|\s)',
    'O-E': r'o[^aeiou]e(?=$|\s)',
    'U-E': r'u[^aeiou]e(?=$|\s)',

    # Ending Consonant Patterns
    '-CK': r'ck(?=$|\s|[^aeiou])',
    '-DGE': r'dge(?=$|\s)',
    '-TCH': r'tch(?=$|\s)',
    '-NG': r'ng(?=$|\s)',
    '-NK': r'nk(?=$|\s)',
    '-FF': r'ff(?=$|\s)',
    '-LL': r'll(?=$|\s)',
    '-SS': r'ss(?=$|\s)',
    '-ZZ': r'zz(?=$|\s)',
    'ALL': r'all',
    '-LD': r'ld(?=$|\s)',
    '-ND': r'nd(?=$|\s)',
    '-ST (long vowel)': r'[aeiou]st(?=$|\s)',

    # Single Letters (uppercase)
    'A': r'(?<![a-z])a(?![a-z])',
    'B': r'b(?![h])',
    'C': r'c(?![eiyh])',
    'D': r'd(?![g])',
    'E': r'(?<![a-z])e(?![a-z])',
    'F': r'f(?![f])',
    'H': r'h(?![aeioucsptw][h])',
    'J': r'j',
    'K': r'k(?![n])',
    'M': r'm',
    'N': r'n(?![gk])',
    'P': r'p(?![h])',
    'QU': r'qu',
    'R': r'r',
    'S': r's(?![sh])',
    'T': r't(?![ch])',
    'V': r'v',
    'W': r'w(?![hr])',
    'X': r'x',
    'Y': r'y(?![aeiou])',
    'Z': r'z(?![z])',

    # Additional Vowel Patterns
    'IE': r'ie',
    'OE': r'oe',
    'UE': r'ue',
    'UI': r'ui',
    'EY (money)': r'ey(?=$|\s)',
    'EI': r'ei',
    'EIGH': r'eigh',

    # Complex Patterns
    'AUGH': r'augh',
    'OUGH': r'ough',
    'EU': r'eu',
    'ES': r'es(?=$|\s)',
    'EAR': r'ear',

    # Silent Letter Combinations
    'KN (silent k)': r'kn',
    'WR (silent w)': r'wr',
    'GN (silent g)': r'gn',

    # Suffix Patterns (uppercase key form)
    '-AGE': r'age(?=$|\s)',
    '-LE (ending)': r'[^aeiou]le(?=$|\s)',
    '-SION': r'sion(?=$|\s)',
    '-TION': r'tion(?=$|\s)',
    '-TURE': r'ture(?=$|\s)',

    # Special Sound Patterns
    'S (z sound between vowels)': r'[aeiou]s[aeiou]',
    'SOFT C (s sound)': r'c[eiy]',
    'SOFT G (j sound)': r'g[eiy]',
    'CH (k sound)': r'ch(?=[aor])',
    'CH (sh sound)': r'ch(?=ef)',
    'OR (er sound - end)': r'or$',
    'AR (er sound - end)': r'ar$',
    'Y (long i - cry)': r'y(?=$|\s)',
    'Y (short i - gym)': r'y(?=[^aeiou\s])',
    
    # Additional common phoneme patterns
    'ON': r'on',
    'IN': r'in',
    'UN': r'un',
    'AN': r'an',
    'EN': r'en',

    # ── Lowercase Single Letters (from curriculum stages) ─────────
    'a': r'a',
    'b': r'b',
    'c': r'c',
    'd': r'd',
    'e': r'e',
    'f': r'f',
    'g': r'g',
    'h': r'h',
    'i': r'i',
    'j': r'j',
    'k': r'k',
    'l': r'l',
    'm': r'm',
    'n': r'n',
    'o': r'o',
    'p': r'p',
    'r': r'r',
    's': r's',
    't': r't',
    'u': r'u',
    'v': r'v',
    'w': r'w',
    'x': r'x',
    'y': r'y',
    'z': r'z',

    # ── Lowercase Split Digraphs (curriculum: a_e, e_e, etc.) ─────
    'a_e': r'a[^aeiou]e(?=$|\s)',
    'e_e': r'e[^aeiou]e(?=$|\s)',
    'i_e': r'i[^aeiou]e(?=$|\s)',
    'o_e': r'o[^aeiou]e(?=$|\s)',
    'u_e': r'u[^aeiou]e(?=$|\s)',
    'y_e': r'y[^aeiou]e(?=$|\s)',

    # ── Lowercase Consonant Clusters & Digraphs (curriculum) ──────
    'sh': r'sh',
    'th': r'th',
    'ch': r'ch',
    'wh': r'wh',
    'ph': r'ph',
    'qu': r'qu',
    'ck': r'ck',
    'dge': r'dge',
    'tch': r'tch',
    'ff': r'ff',
    'ss': r'ss',
    'zz': r'zz',
    'll': r'll',
    'rr': r'rr',
    'kn': r'kn',
    'wr': r'wr',
    'sc': r'sc',

    # ── Lowercase Consonant Blends ────────────────────────────────
    'bl': r'bl',
    'cl': r'cl',
    'fl': r'fl',
    'gl': r'gl',
    'pl': r'pl',
    'sl': r'sl',
    'br': r'br',
    'cr': r'cr',
    'dr': r'dr',
    'fr': r'fr',
    'gr': r'gr',
    'pr': r'pr',
    'tr': r'tr',
    'vr': r'vr',
    'sk': r'sk',
    'sm': r'sm',
    'sn': r'sn',
    'sp': r'sp',
    'st': r'st',
    'sw': r'sw',
    'tw': r'tw',
    'ft': r'ft',
    'lf': r'lf',
    'lp': r'lp',
    'lt': r'lt',
    'ps': r'ps',
    'mn': r'mn',

    # ── Lowercase Ending Clusters ─────────────────────────────────
    'ng': r'ng',
    'nk': r'nk',
    'nd': r'nd',
    'nt': r'nt',

    # ── Lowercase Vowel Patterns (curriculum) ─────────────────────
    'ai': r'ai',
    'ay': r'ay',
    'ee': r'ee',
    'ea': r'ea',
    'oo': r'oo',
    'oa': r'oa',
    'ow': r'ow',
    'oi': r'oi',
    'oy': r'oy',
    'ou': r'ou',
    'au': r'au',
    'aw': r'aw',
    'ew': r'ew',
    'ie': r'ie',
    'oe': r'oe',
    'ue': r'ue',
    'ei': r'ei',
    'ey': r'ey',
    'eigh': r'eigh',
    'igh': r'igh',
    'ar': r'ar',
    'er': r'er',
    'ir': r'ir',
    'or': r'or',
    'ur': r'ur',
    'ear': r'ear',
    'air': r'air',
    'are': r'are',
    'ore': r'ore',
    'oar': r'oar',
    'ure': r'ure',
    'al': r'al',
    'el': r'el',
    'le': r'le',
    'augh': r'augh',
    'ough': r'ough',
    'eu': r'eu',

    # ── English Suffixes (from advanced curriculum stages) ─────────
    '-ed': r'ed(?=$|\s)',
    '-s': r's(?=$|\s)',
    '-es': r'es(?=$|\s)',
    '-er': r'er(?=$|\s)',
    '-est': r'est(?=$|\s)',
    '-ing': r'ing(?=$|\s)',
    '-y': r'(?<=[a-z])y(?=$|\s)',
    '-ly': r'ly(?=$|\s)',
    '-ful': r'ful(?=$|\s)',
    '-less': r'less(?=$|\s)',
    '-ness': r'ness(?=$|\s)',
    '-ment': r'ment(?=$|\s)',
    '-al': r'(?<=[a-z])al(?=$|\s)',
    '-all': r'all(?=$|\s)',
    '-ary': r'ary(?=$|\s)',
    '-ery': r'ery(?=$|\s)',
    '-ory': r'ory(?=$|\s)',
    '-ation': r'ation(?=$|\s)',
    '-tion': r'tion(?=$|\s)',
    '-sion': r'sion(?=$|\s)',
    '-ssion': r'ssion(?=$|\s)',
    '-sure': r'sure(?=$|\s)',
    '-ture': r'ture(?=$|\s)',
    '-ous': r'ous(?=$|\s)',
    '-ious': r'ious(?=$|\s)',
    '-eous': r'eous(?=$|\s)',
    '-tious': r'tious(?=$|\s)',
    '-cious': r'cious(?=$|\s)',
    '-ive': r'ive(?=$|\s)',
    '-itive': r'itive(?=$|\s)',
    '-ative': r'ative(?=$|\s)',
    '-ible': r'ible(?=$|\s)',
    '-able': r'able(?=$|\s)',
    '-ibly': r'ibly(?=$|\s)',
    '-ably': r'ably(?=$|\s)',
    '-ant': r'ant(?=$|\s)',
    '-ent': r'ent(?=$|\s)',
    '-ance': r'ance(?=$|\s)',
    '-ence': r'ence(?=$|\s)',
    '-ial': r'ial(?=$|\s)',
    '-ual': r'ual(?=$|\s)',
    '-ular': r'ular(?=$|\s)',
    '-ical': r'ical(?=$|\s)',
    '-cian': r'cian(?=$|\s)',
    '-ology': r'ology(?=$|\s)',
    '-ify': r'ify(?=$|\s)',
    '-ise': r'ise(?=$|\s)',
    '-ize': r'ize(?=$|\s)',
    '-esque': r'esque(?=$|\s)',
    '-ette': r'ette(?=$|\s)',
    '-ward': r'ward(?=$|\s)',
    '-wise': r'wise(?=$|\s)',

    # ── English Ending Patterns (curriculum) ──────────────────────
    '-ild': r'ild(?=$|\s)',
    '-ind': r'ind(?=$|\s)',
    '-old': r'old(?=$|\s)',
    '-oll': r'oll(?=$|\s)',
    '-olt': r'olt(?=$|\s)',
    '-ost': r'ost(?=$|\s)',
    '-ull': r'ull(?=$|\s)',

    # ── English Word Roots & Latin-origin Endings ─────────────────
    '-graph': r'graph(?=$|\s)',
    '-phon': r'phon(?=$|\s)',
    '-scope': r'scope(?=$|\s)',
    '-form': r'form(?=$|\s)',
    '-ject': r'ject(?=$|\s)',
    '-rupt': r'rupt(?=$|\s)',
    '-struct': r'struct(?=$|\s)',
    '-duct': r'duct(?=$|\s)',
    '-port': r'port(?=$|\s)',
    '-mit': r'mit(?=$|\s)',
    '-scribe': r'scribe(?=$|\s)',

    # ── English Prefixes (from advanced curriculum stages) ─────────
    'un-': r'(?<=\b)un',
    're-': r'(?<=\b)re',
    'dis-': r'(?<=\b)dis',
    'mis-': r'(?<=\b)mis',
    'pre-': r'(?<=\b)pre',
    'non-': r'(?<=\b)non',
    'over-': r'(?<=\b)over',
    'under-': r'(?<=\b)under',
    'anti-': r'(?<=\b)anti',
    'auto-': r'(?<=\b)auto',
    'bi-': r'(?<=\b)bi',
    'bio-': r'(?<=\b)bio',
    'circum-': r'(?<=\b)circum',
    'com-': r'(?<=\b)com',
    'con-': r'(?<=\b)con',
    'counter-': r'(?<=\b)counter',
    'de-': r'(?<=\b)de',
    'ex-': r'(?<=\b)ex',
    'fore-': r'(?<=\b)fore',
    'il-': r'(?<=\b)il',
    'im-': r'(?<=\b)im',
    'in-': r'(?<=\b)in',
    'inter-': r'(?<=\b)inter',
    'ir-': r'(?<=\b)ir(?=[rv])',
    'micro-': r'(?<=\b)micro',
    'multi-': r'(?<=\b)multi',
    'post-': r'(?<=\b)post',
    'pro-': r'(?<=\b)pro',
    'semi-': r'(?<=\b)semi',
    'sub-': r'(?<=\b)sub',
    'super-': r'(?<=\b)super',
    'tele-': r'(?<=\b)tele',
    'trans-': r'(?<=\b)trans',
    'tri-': r'(?<=\b)tri',
    'uni-': r'(?<=\b)uni',

    # ══════════════════════════════════════════════════════════════════
    # FRENCH PHONEME PATTERNS
    # ══════════════════════════════════════════════════════════════════

    # Accented vowels
    'é': r'é',
    'è': r'è',
    'ê': r'ê',

    # French digraphs & nasal vowels
    'an': r'an',
    'en': r'en',
    'on': r'on',
    'in': r'in',
    'un': r'un',
    'ain': r'ain',
    'ein': r'ein',
    'oin': r'oin',
    'ien': r'ien',

    # French consonant combinations
    'gn': r'gn',
    'ill': r'ill',
    'gu': r'gu',
    'ge': r'ge',
    'gi': r'gi',
    'ce': r'ce',
    'ci': r'ci',

    # French vowel combinations
    'eau': r'eau',
    'ail': r'ail',
    'eil': r'eil',
    'euil': r'euil',
    'oeil': r'oeil',
    'euille': r'euille',

    # French endings & suffixes
    'ez': r'ez',
    'tion': r'tion',
    'sion': r'sion',
    '-eur': r'eur',
    '-euse': r'euse',
    '-eux': r'eux',
    '-oir': r'oir',
    '-oire': r'oire',
    'em': r'em',
    'am': r'am',
    'om': r'om',
    'im': r'im',
    'um': r'um',

    # French silent letter patterns
    'e muet': r'e(?=$|\s)',   # Silent e at end of word
    'h muet': r'(?<=\b)h',   # Silent h at start of word
    's muet': r's(?=$|\s)',   # Silent s at end of word
    'x muet': r'x(?=$|\s)',   # Silent x at end of word

    # French prefixes
    'des-': r'(?<=\b)des',
    'dés-': r'(?<=\b)dés',

    # ══════════════════════════════════════════════════════════════════
    # SPANISH PHONEME PATTERNS
    # ══════════════════════════════════════════════════════════════════

    # Accented vowels
    'á': r'á',
    'í': r'í',
    'ó': r'ó',
    'ú': r'ú',

    # Spanish digraphs
    'ñ': r'ñ',

    # Spanish syllable patterns
    'ca': r'ca',
    'co': r'co',
    'cu': r'cu',
    'que': r'que',
    'qui': r'qui',
    'ga': r'ga',
    'go': r'go',
    'güe': r'güe',
    'güi': r'güi',
    'za': r'za',
    'zo': r'zo',
    'zu': r'zu',
    'je': r'je',
    'ji': r'ji',

    # Spanish diphthongs
    'ia': r'ia',
    'io': r'io',
    'iu': r'iu',
    'ua': r'ua',
    'uo': r'uo',

    # Spanish suffixes
    '-ción': r'ción',
    '-sión': r'sión',
    '-mente': r'mente',
    '-oso': r'oso',
    '-osa': r'osa',
    '-dad': r'dad',
    '-idad': r'idad',
    '-eza': r'eza',
    '-anza': r'anza',
    '-encia': r'encia',
    '-ancia': r'ancia',

    # Spanish consonant clusters
    'mb': r'mb',
    'mp': r'mp',
    'h muda': r'h',
}

# Build a case-insensitive, Unicode-normalized lookup for phoneme patterns.
# This ensures lookups work regardless of whether the key arrives as 'EI', 'ei',
# or with different Unicode normalization (NFC vs NFD for accented chars like è).
# First occurrence wins if there are case collisions (English uppercase has priority
# since it appears first in the dict).
_NORMALIZED_PHONEME_LOOKUP = {}
for _key, _pattern in PHONEME_REGEX_PATTERNS.items():
    _norm_key = unicodedata.normalize('NFC', _key.lower())
    if _norm_key not in _NORMALIZED_PHONEME_LOOKUP:
        _NORMALIZED_PHONEME_LOOKUP[_norm_key] = _pattern

class ImageProcessor:
    
    @staticmethod
    def resize_image(source_path: str, output_path: str, size: tuple = (200, 266)) -> str:
        """
        Resize an image to a specified size.

        Parameters:
        source_path (str): Path to the source image file.
        output_path (str): Path to save the resized image.
        size (tuple): Desired output size (width, height).

        Returns:
        str: Path to the resized image (same as output_path).
        """
        try:
            # Remove file:// prefix if present for cv2
            clean_source_path = source_path.replace("file://", "")

            image = cv2.imread(clean_source_path)
            if image is None:
                raise ValueError(f"Unable to read image at {clean_source_path}")

            # Use INTER_AREA for shrinking, INTER_LINEAR or INTER_CUBIC for enlarging
            # Assuming thumbnails are mostly shrinking.
            resized_image = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
            
            # Ensure parent directory for output_path exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            cv2.imwrite(output_path, resized_image, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            logger.info(f"Resized image saved to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error resizing image {source_path} to {output_path}: {str(e)}")
            raise e

    @staticmethod
    def find_least_complex_text_position(image_path, preloaded_image=None):
        """
        Find the best Y position for text by choosing the horizontal band
        (top or bottom of the image) with the least visual complexity.

        Uses Canny edge detection to measure how "busy" each band is.
        Only considers top (5%-30%) and bottom (70%-95%) bands to avoid
        the middle where characters/action typically sit.

        Parameters:
        image_path (str): Path to the input image
        preloaded_image: Optional pre-loaded cv2 image array to avoid re-reading from disk.

        Returns:
        int: The Y coordinate (center of the chosen band)
        """
        if preloaded_image is not None:
            image = preloaded_image
        else:
            clean_path = image_path.replace("file://", "")
            image = cv2.imread(clean_path)
        if image is None:
            raise ValueError(f"Unable to read image at {image_path}")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Light blur to reduce noise before edge detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        h = image.shape[0]

        # Define candidate bands: top and bottom of the image
        top_band = edges[int(h * 0.05):int(h * 0.30), :]
        bottom_band = edges[int(h * 0.70):int(h * 0.95), :]

        # Edge density = proportion of edge pixels in the band
        top_density = np.mean(top_band > 0)
        bottom_density = np.mean(bottom_band > 0)

        logger.info(
            f"Text placement — edge density: top={top_density:.3f}, bottom={bottom_density:.3f}"
        )

        if top_density <= bottom_density:
            # Top band is cleaner — place text at ~17.5% (center of 5%-30%)
            return int(h * 0.175)
        else:
            # Bottom band is cleaner — place text at ~82.5% (center of 70%-95%)
            return int(h * 0.825)

    @staticmethod
    def find_light_area_center_of_gravity(
        image_path, threshold_percentage=0.9, min_area=1000, weighted=True
    ):
        """
        Find the center of gravity of light areas in an image based on intensity values.

        Parameters:
        image_path (str): Path to the input image
        threshold_percentage (float): Value between 0-1 to determine what's considered "light"
        min_area (int): Minimum area size to consider
        weighted (bool): If True, uses intensity values as weights for CoG calculation

        Returns:
        tuple: (x, y) coordinates of the center of gravity of the largest light area,
            largest region coordinates, binary image
        """
        # Remove file:// prefix if present for cv2
        clean_path = image_path.replace("file://", "")

        # Read the image
        image = cv2.imread(clean_path)
        if image is None:
            raise ValueError(f"Unable to read image at {clean_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Calculate threshold value based on the percentage of the maximum intensity
        max_intensity = 255
        threshold_value = int(max_intensity * threshold_percentage)

        # Create binary mask for light areas
        _, binary = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)

        # Find connected components
        labels = measure.label(binary, connectivity=2)
        regions = measure.regionprops(labels, intensity_image=gray)

        # If no regions found, return center of the image
        if not regions:
            return (image.shape[1] // 2, image.shape[0] // 2), None, binary

        # Filter regions based on size and find the largest one
        viable_regions = [region for region in regions if region.area >= min_area]
        if not viable_regions:
            return (image.shape[1] // 2, image.shape[0] // 2), None, binary

        largest_region = max(viable_regions, key=lambda x: x.area)
        coords = largest_region.coords  # (y, x) format

        if weighted:
            # Create a mask of just this region
            region_mask = np.zeros_like(gray)
            for y, x in coords:
                region_mask[y, x] = 1

            # Multiply the gray image by the mask to get only the pixels in this region
            masked_gray = gray * region_mask

            # Calculate the weighted centroid (center of gravity)
            total_weight = np.sum(masked_gray)
            if total_weight == 0:  # Fallback in case of division by zero
                return (
                    (int(largest_region.centroid[1]), int(largest_region.centroid[0])),
                    coords,
                    binary,
                )

            # Calculate weighted sum of x and y coordinates
            h, w = gray.shape
            y_indices, x_indices = np.mgrid[0:h, 0:w]
            x_weighted_sum = np.sum(x_indices * masked_gray)
            y_weighted_sum = np.sum(y_indices * masked_gray)

            # Calculate the center of gravity
            x_cog = x_weighted_sum / total_weight
            y_cog = y_weighted_sum / total_weight
        else:
            # Use the standard centroid if not using weighted calculation
            y_cog, x_cog = largest_region.centroid

        # Return the center of gravity coordinates and the region coordinates
        return (int(x_cog), int(y_cog)), coords, binary

    @staticmethod
    def find_phoneme_positions_with_regex(text: str, selected_phoneme_keys: List[str]) -> Set[int]:
        """
        Find all character positions in the text that are part of any selected phoneme,
        using regex patterns.

        Args:
            text (str): The text to search within.
            selected_phoneme_keys (List[str]): A list of phoneme keys (e.g., "SH", "A-E")
                                               for which to find occurrences.

        Returns:
            Set[int]: A set of character indices in the original text that should be highlighted.
        """
        positions_to_highlight = set()

        for phoneme_key in selected_phoneme_keys:
            # Try exact match first, then fall back to case-insensitive normalized lookup
            pattern_str = PHONEME_REGEX_PATTERNS.get(phoneme_key)
            if not pattern_str:
                norm_key = unicodedata.normalize('NFC', phoneme_key.lower())
                pattern_str = _NORMALIZED_PHONEME_LOOKUP.get(norm_key)
            if pattern_str:
                try:
                    regex = re.compile(pattern_str, re.IGNORECASE)
                    # Find all non-overlapping matches
                    for match in regex.finditer(text):
                        # Add all indices covered by this match to the set
                        for i in range(match.start(), match.end()):
                            positions_to_highlight.add(i)
                except re.error as e:
                    logger.error(f"Regex error for phoneme key '{phoneme_key}' with pattern '{pattern_str}': {e}")
            else:
                # Fallback: treat as a literal morpheme (e.g. "-ing", "un-", "struct")
                # Strip leading/trailing dashes and parenthetical annotations for matching
                clean_key = phoneme_key.split('(')[0].strip().strip('-').strip()
                if clean_key:
                    try:
                        escaped = re.escape(clean_key)
                        regex = re.compile(escaped, re.IGNORECASE)
                        for match in regex.finditer(text):
                            for i in range(match.start(), match.end()):
                                positions_to_highlight.add(i)
                    except re.error as e:
                        logger.error(f"Regex error for morphology key '{phoneme_key}' (cleaned: '{clean_key}'): {e}")
                else:
                    logger.warning(f"No regex pattern found for key: '{phoneme_key}'")
        return positions_to_highlight

    @staticmethod
    def parse_manual_highlights(text: str) -> tuple[str, set[int]]:
        """
        Strips HTML tags (<mark>, etc) from text and returns the clean text,
        while recording the character indices of any text that was inside a <mark> tag.
        Returns (clean_text, highlight_indices)
        """
        clean_text = ""
        highlight_indices = set()
        is_highlighted = False
        
        i = 0
        while i < len(text):
            if text[i:].startswith('</mark>'):
                is_highlighted = False
                i += 7
            elif text[i:].startswith('<mark'):
                # Start index of the next tag closing bracket
                end_tag = text.find('>', i)
                if end_tag != -1:
                    is_highlighted = True
                    i = end_tag + 1
                else:
                    i += 5
            elif text[i] == '<':
                # Skip other HTML tags entirely (like <p>, <br>) if any snuck in
                end_tag = text.find('>', i)
                if end_tag != -1:
                    i = end_tag + 1
                else:
                    # Broken tag, just append
                    clean_text += text[i]
                    i += 1
            else:
                if is_highlighted:
                    highlight_indices.add(len(clean_text))
                clean_text += text[i]
                i += 1
                
        return clean_text, highlight_indices

    @staticmethod
    def add_text_to_image(
        image_path,
        text,
        output_path,
        font_path,
        phonemes: List[str],
        font_scale=2.5,
        text_color=(0, 0, 255),
        stroke_color=(255, 255, 255),
        stroke_thickness=8,
        use_weighted_cog=True,
        letter_spacing=5,
        preloaded_image=None,
    ):
        """
        Add text to an image at the center of gravity of the largest light area using custom font,
        with special highlighting for specified phonemes using regex.

        Parameters:
        image_path (str): Path to the input image
        text (str): Text to add to the image
        output_path (str): Path to save the output image
        font_path (str): Path to custom font file
        phonemes (List[str]): List of phoneme KEYS (e.g., "SH", "A-E") to highlight.
        font_scale (float): Scale factor for text size
        text_color (tuple): Color of the text (BGR)
        stroke_color (tuple): Color of the stroke (BGR)
        stroke_thickness (int): Thickness of the stroke
        use_weighted_cog (bool): Whether to use intensity-weighted center of gravity
        letter_spacing (int): Spacing between letters in pixels
        preloaded_image: Optional pre-loaded cv2 image array to avoid re-reading from disk.

        Returns:
        str: Path to the processed image
        """
        # Remove file:// prefix if present for cv2
        clean_path = image_path.replace("file://", "")

        # 1. Parse manual HTML highlights and strip tags from the raw text for PIL
        # Convert legacy ** to <mark> for unified parsing
        if '**' in text:
            import re
            text = re.sub(r'\*\*(.*?)\*\*', r'<mark>\1</mark>', text)

        has_manual_highlights = '<mark' in text
        if has_manual_highlights:
            text, manual_highlight_indices = ImageProcessor.parse_manual_highlights(text)
        else:
            # Still run through parse to strip any <p> or <br> tags from Tiptap before drawing
            text, _ = ImageProcessor.parse_manual_highlights(text)
            manual_highlight_indices = set()

        # Read the image (reuse preloaded data if available)
        if preloaded_image is not None:
            image_data = preloaded_image
        else:
            image_data = cv2.imread(clean_path)
        if image_data is None:
            raise ValueError(f"Unable to read image at {clean_path}")

        # Find the best Y position by picking the least visually complex band
        # (top or bottom of the image — avoids the middle where characters sit)
        try:
            center_y = ImageProcessor.find_least_complex_text_position(clean_path, preloaded_image=image_data)
            center_x = image_data.shape[1] // 2
        except Exception as e:
            logger.warning(f"Could not find text position, defaulting to top: {e}")
            center_x = image_data.shape[1] // 2
            center_y = int(image_data.shape[0] * 0.175)

        # Convert OpenCV image to PIL image
        pil_image = Image.fromarray(cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        # Calculate available space for text based on image dimensions
        img_width, img_height = pil_image.size
        max_text_width = img_width * 0.8  # 80% of image width

        # Safe font loader to handle corrupt/unsupported TTF files (e.g. OpenDyslexic in PIL)
        def _load_font(path, size):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                import os # fallback to reliable font in the same dir
                fallback = os.path.join(os.path.dirname(path), 'LexieReadable-Regular.ttf')
                try:
                    return ImageFont.truetype(fallback, size)
                except Exception:
                    return ImageFont.load_default(size)

        initial_font_size = int(min(img_width, img_height) * 0.1 * font_scale)
        font_size = initial_font_size
        font = _load_font(font_path, font_size)

        # Split text into words for wrapping
        words = text.split()

        def get_text_width_with_spacing(text_to_measure, font_obj, spacing):
            if not text_to_measure:
                return 0
            char_widths = [int(font_obj.getlength(char)) for char in text_to_measure]
            return sum(char_widths) + spacing * (len(text_to_measure) - 1 if len(text_to_measure) > 0 else 0)

        text_length = len(text)
        if text_length > 60:
            font_size_adjustment = max(0.7, 1.0 - (text_length - 60) / 200)
            font_size = int(font_size * font_size_adjustment)
            font = _load_font(font_path, font_size)
            letter_spacing = max(1, letter_spacing - 1)
        elif text_length > 40:
            font_size_adjustment = max(0.85, 1.0 - (text_length - 40) / 200)
            font_size = int(font_size * font_size_adjustment)
            font = _load_font(font_path, font_size)

        lines = []
        current_line = []
        for word in words:
            test_line = current_line + [word]
            test_line_text = " ".join(test_line)
            text_width_calc = get_text_width_with_spacing(test_line_text, font, letter_spacing)
            if text_width_calc <= max_text_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
        if current_line:
            lines.append(" ".join(current_line))

        line_height = font_size * 1.2
        total_text_height = len(lines) * line_height

        if len(lines) > 1:
            max_y_position = img_height - total_text_height - 20
            if center_y + (total_text_height / 2) > max_y_position:
                center_y = max(center_y - (total_text_height / 4), img_height * 0.2)

        start_y = center_y - (total_text_height / 2)
        min_start_y = img_height * 0.08
        if start_y < min_start_y:
            start_y = min_start_y
        if start_y + total_text_height > img_height - 10:
            if len(lines) > 1:
                line_height = min(line_height, (img_height - 20) / len(lines))
                total_text_height = len(lines) * line_height
                start_y = max(min_start_y, img_height - total_text_height - 10)


        # ── Draw dual-layer drop shadow behind ALL text lines ──
        # Layer 1: Wide soft glow — separates text from busy backgrounds
        # Layer 2: Tight crisp shadow — adds depth and definition
        # Adapt shadow color to contrast with text
        text_brightness = (text_color[0] + text_color[1] + text_color[2]) / 3
        if text_brightness < 128:
            glow_color = (255, 255, 255, 200)   # light glow for dark text
            shadow_color = (255, 255, 255, 240)  # light crisp shadow
        else:
            glow_color = (0, 0, 0, 200)          # dark glow for light text
            shadow_color = (0, 0, 0, 240)        # dark crisp shadow

        def _draw_text_on_layer(layer_draw, offset_x, offset_y, color):
            """Helper to draw all text lines on a layer with offset."""
            for si, shadow_line_text in enumerate(lines):
                shadow_line_w = get_text_width_with_spacing(shadow_line_text, font, letter_spacing)
                sx = center_x - shadow_line_w // 2 + offset_x
                sy = start_y + (si * line_height) + offset_y
                cur_sx = sx
                for sc in shadow_line_text:
                    layer_draw.text((cur_sx, sy), sc, font=font, fill=color)
                    cur_sx += int(font.getlength(sc)) + letter_spacing

        # Layer 1: Wide soft glow (large blur radius, centered behind text)
        glow_layer = Image.new("RGBA", pil_image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        _draw_text_on_layer(glow_draw, 0, 0, glow_color)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=int(font_size * 0.40)))
        pil_image = Image.alpha_composite(pil_image.convert("RGBA"), glow_layer).convert("RGB")

        # Layer 2: Tight crisp shadow (small blur, offset for depth)
        shadow_layer = Image.new("RGBA", pil_image.size, (0, 0, 0, 0))
        shadow_draw_layer = ImageDraw.Draw(shadow_layer)
        _draw_text_on_layer(shadow_draw_layer, int(font_size * 0.05), int(font_size * 0.07), shadow_color)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=int(font_size * 0.08)))
        pil_image = Image.alpha_composite(pil_image.convert("RGBA"), shadow_layer).convert("RGB")
        draw = ImageDraw.Draw(pil_image)  # Re-create draw on composited image

        for i, line_text in enumerate(lines):
            text_width_line = get_text_width_with_spacing(line_text, font, letter_spacing)
            text_x = center_x - text_width_line // 2
            text_y = start_y + (i * line_height)

            # Determine highlighting: manual override or auto regex
            if has_manual_highlights:
                # We need to map the global manual indices to this specific line
                # Calculate what index this line starts at globally, accounting for spaces between lines
                global_line_start = sum(len(lines[j]) + 1 for j in range(i))
                phoneme_char_indices = {idx - global_line_start for idx in manual_highlight_indices 
                                        if global_line_start <= idx < global_line_start + len(line_text)}
            else:
                phoneme_char_indices = ImageProcessor.find_phoneme_positions_with_regex(line_text, phonemes)

            # Phoneme highlight — warm cream pill with underline accent.
            PHONEME_BG_RGBA = (255, 240, 210, 215)   # warm cream, ~84% opacity
            PHONEME_TEXT_RGB = (120, 53, 15)          # #78350f  dark brown
            UNDERLINE_RGB = (212, 149, 107)           # #d4956b  warm terracotta accent
            HIGHLIGHT_PAD_X = max(int(font_size * 0.15), 4)
            HIGHLIGHT_PAD_Y = max(int(font_size * 0.13), 3)
            HIGHLIGHT_RADIUS = max(int(font_size * 0.28), 7)
            UNDERLINE_HEIGHT = max(int(font_size * 0.07), 2)

            # Pre-compute per-character widths
            char_widths = []
            for ch in line_text:
                char_widths.append(int(font.getlength(ch)))

            # Draw highlight pill backgrounds first (behind all text)
            # Use an alpha-composited overlay for the soft translucent pill
            highlight_runs = []
            pre_x = text_x
            run_start = None
            for char_idx in range(len(line_text) + 1):
                in_run = char_idx < len(line_text) and char_idx in phoneme_char_indices
                if in_run and run_start is None:
                    run_start = (char_idx, pre_x)
                elif not in_run and run_start is not None:
                    rx1 = run_start[1] - HIGHLIGHT_PAD_X
                    ry1 = text_y - HIGHLIGHT_PAD_Y
                    rx2 = pre_x + HIGHLIGHT_PAD_X
                    ry2 = text_y + font_size + HIGHLIGHT_PAD_Y
                    highlight_runs.append((rx1, ry1, rx2, ry2))
                    run_start = None
                if char_idx < len(line_text):
                    pre_x += char_widths[char_idx] + letter_spacing

            # Draw translucent pill backgrounds via alpha composite
            if highlight_runs:
                overlay = Image.new('RGBA', pil_image.size, (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                for (rx1, ry1, rx2, ry2) in highlight_runs:
                    overlay_draw.rounded_rectangle(
                        [rx1, ry1, rx2, ry2],
                        radius=HIGHLIGHT_RADIUS,
                        fill=PHONEME_BG_RGBA,
                    )
                    # Crisp underline accent just below the pill
                    underline_y = ry2 + 1
                    overlay_draw.rectangle(
                        [rx1 + 2, underline_y, rx2 - 2, underline_y + UNDERLINE_HEIGHT],
                        fill=UNDERLINE_RGB + (230,),
                    )
                pil_image = Image.alpha_composite(pil_image.convert('RGBA'), overlay).convert('RGB')
                draw = ImageDraw.Draw(pil_image)

            # Draw characters
            current_x_pos = text_x
            for char_idx, char_to_draw in enumerate(line_text):
                is_phoneme_char = char_idx in phoneme_char_indices

                if is_phoneme_char:
                    # Highlighted phoneme: very slight warm tint (~5% shift) so
                    # phoneme chars are subtly distinguishable from surrounding text.
                    r, g, b = text_color[2], text_color[1], text_color[0]
                    pil_text_color = (
                        min(255, int(r * 0.95 + 230 * 0.05)),
                        min(255, int(g * 0.95 + 200 * 0.05)),
                        min(255, int(b * 0.95 + 160 * 0.05)),
                    )
                    pil_stroke_color = (stroke_color[2], stroke_color[1], stroke_color[0])
                    for offset_x in range(-stroke_thickness, stroke_thickness + 1, 1):
                        for offset_y in range(-stroke_thickness, stroke_thickness + 1, 1):
                            if stroke_thickness > 0 and offset_x == 0 and offset_y == 0:
                                continue
                            draw.text(
                                (current_x_pos + offset_x, text_y + offset_y),
                                char_to_draw,
                                font=font,
                                fill=pil_stroke_color,
                            )
                    draw.text(
                        (current_x_pos, text_y),
                        char_to_draw,
                        font=font,
                        fill=pil_text_color,
                    )
                else:
                    # Regular text with stroke
                    pil_text_color = (text_color[2], text_color[1], text_color[0])
                    pil_stroke_color = (stroke_color[2], stroke_color[1], stroke_color[0])
                    for offset_x in range(-stroke_thickness, stroke_thickness + 1, 1):
                        for offset_y in range(-stroke_thickness, stroke_thickness + 1, 1):
                            if stroke_thickness > 0 and offset_x == 0 and offset_y == 0:
                                continue
                            draw.text(
                                (current_x_pos + offset_x, text_y + offset_y),
                                char_to_draw,
                                font=font,
                                fill=pil_stroke_color,
                            )
                    draw.text(
                        (current_x_pos, text_y),
                        char_to_draw,
                        font=font,
                        fill=pil_text_color,
                    )
                current_x_pos += char_widths[char_idx] + letter_spacing

        processed_pil_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, processed_pil_image, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        return output_path
    
    @staticmethod
    def generate_cover_page(
        image_path,
        text,
        output_path,
        font_path,
        font_scale=20,
        text_color=(0, 0, 255),
        stroke_color=(255, 255, 255),
        stroke_thickness=8,
        letter_spacing=5,
        badge_text="Badge",
        badge_rotation_angle=30,
        series_label=None,
    ):
        """
        Generate a cover page by adding text to an image and overlaying a badge.

        Parameters:
        image_path (str): Path to the input image
        text (str): Text to add to the image
        output_path (str): Path to save the output image
        font_path (str): Path to custom font file
        font_scale (float): Scale factor for text size
        text_color (tuple): Color of the text (BGR)
        stroke_color (tuple): Color of the stroke (BGR)
        stroke_thickness (int): Thickness of the stroke
        letter_spacing (int): Spacing between letters in pixels
        badge_text (str): Text to display on the badge
        badge_rotation_angle (int): Angle to rotate the badge
        series_label (str or None): Series identification text (e.g., "BOOK 3 OF 6")

        Returns:
        str: Path to the processed image
        """
        # Remove file:// prefix if present for cv2
        clean_path = image_path.replace("file://", "")

        # Read the image
        image = cv2.imread(clean_path)
        if image is None:
            raise ValueError(f"Unable to read image at {clean_path}")

        # Convert OpenCV image to PIL image
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_image)

        # Calculate available space for text based on image dimensions
        img_width, img_height = pil_image.size
        max_text_width = img_width * 0.8  # 80% of image width

        # Start with a reasonable font size based on image dimensions
        font_size = int(min(img_width, img_height) * 0.1 * font_scale)
        try:
            font = ImageFont.truetype(font_path, font_size)
        except OSError:
            import os
            fallback = os.path.join(os.path.dirname(font_path), 'LexieReadable-Bold.ttf')
            if not os.path.exists(fallback): fallback = os.path.join(os.path.dirname(font_path), 'LexieReadable-Regular.ttf')
            try:
                font = ImageFont.truetype(fallback, font_size)
            except Exception:
                font = ImageFont.load_default()

        # Split text into words for wrapping
        words = text.split()

        # Function to calculate text width with custom letter spacing
        def get_text_width_with_spacing(text, font, spacing):
            if not text:
                return 0
            char_widths = [draw.textbbox((0, 0), char, font=font)[2] for char in text]
            return sum(char_widths) + spacing * (len(text) - 1)

        lines = []
        current_line = []

        # Word wrap algorithm with letter spacing consideration
        for word in words:
            test_line = current_line + [word]
            test_line_text = " ".join(test_line)
            text_width = get_text_width_with_spacing(
                test_line_text, font, letter_spacing
            )

            if text_width <= max_text_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        # Calculate total text height for all lines
        line_height = font_size * 1.2  # Add some spacing between lines

        # Calculate starting y position to center all lines vertically
        start_y = 50
        badge_position_y = int(start_y + len(lines) * line_height)

        text_color_rgb = (text_color[2], text_color[1], text_color[0])  # BGR to RGB
        stroke_color_rgb = (
            stroke_color[2],
            stroke_color[1],
            stroke_color[0],
        )  # BGR to RGB

        # Draw each line with custom letter spacing
        for i, line in enumerate(lines):
            text_width = get_text_width_with_spacing(line, font, letter_spacing)
            text_x = (img_width - text_width) // 2  # Center the text horizontally
            text_y = start_y + (i * line_height)

            current_x = text_x
            for char in line:
                # Draw text stroke (outline) for each character
                for offset_x in range(-stroke_thickness, stroke_thickness + 1, 1):
                    for offset_y in range(-stroke_thickness, stroke_thickness + 1, 1):
                        draw.text(
                            (current_x + offset_x, text_y + offset_y),
                            char,
                            font=font,
                            fill=stroke_color_rgb,
                        )

                # Draw main text for each character
                draw.text((current_x, text_y), char, font=font, fill=text_color_rgb)

                # Move to the next character position with custom spacing
                char_width = draw.textbbox((0, 0), char, font=font)[2]
                current_x += char_width + letter_spacing

        # Add badge to the image
        def add_badge_to_image(img, badge_text, rotation_angle):
            font = ImageFont.load_default(25)

            # Create a temporary image to measure text
            temp_img = Image.new("RGBA", (1, 1))
            temp_draw = ImageDraw.Draw(temp_img)
            text_bbox = temp_draw.textbbox((0, 0), badge_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # Create badge dimensions with padding
            padding_x, padding_y = 12, 8
            badge_width = text_width + padding_x * 2
            badge_height = text_height + padding_y * 4

            # Create a transparent badge image
            badge_img = Image.new("RGBA", (badge_width, badge_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(badge_img)

            # Draw rounded rectangle for badge
            draw.rounded_rectangle(
                [(0, 0), (badge_width, badge_height)], radius=25, fill=stroke_color_rgb
            )

            # Draw text on badge
            text_x = padding_x
            text_y = padding_y
            draw.text((text_x, text_y), badge_text, font=font, fill=text_color_rgb)

            # Rotate the badge
            rotated_badge = badge_img.rotate(
                rotation_angle, expand=True, resample=Image.BICUBIC
            )

            # Calculate paste position (centered at the requested position)
            paste_x = 700 - rotated_badge.width
            paste_y = badge_position_y

            # Paste the badge onto the original image
            img.paste(rotated_badge, (paste_x, paste_y), rotated_badge)

            return img

        # Add badge to the image (only if badge_text is provided)
        if badge_text:
            pil_image_with_badge = add_badge_to_image(
                pil_image, badge_text, badge_rotation_angle
            )
        else:
            pil_image_with_badge = pil_image

        # Convert back to OpenCV image
        image_with_badge = cv2.cvtColor(
            np.array(pil_image_with_badge), cv2.COLOR_RGB2BGR
        )

        # Save the final image
        cv2.imwrite(output_path, image_with_badge, [int(cv2.IMWRITE_JPEG_QUALITY), 75])

        # ── Series badge — prominent top banner ──────────────────────
        if series_label:
            # Re-open with PIL for the series badge overlay
            badge_pil = Image.open(output_path).convert("RGBA")
            bw, bh = badge_pil.size

            # Font size scales with image width (roughly 4.5% of width — much more visible)
            series_font_size = max(24, int(bw * 0.045))
            try:
                series_font = ImageFont.truetype(font_path, series_font_size)
            except Exception:
                series_font = ImageFont.load_default(series_font_size)

            # Measure text
            temp_draw = ImageDraw.Draw(badge_pil)
            text_bbox = temp_draw.textbbox((0, 0), series_label, font=series_font)
            tw = text_bbox[2] - text_bbox[0]
            th = text_bbox[3] - text_bbox[1]

            # Banner dimensions — full-width strip across the top
            pad_y = int(series_font_size * 0.55)
            banner_h = th + pad_y * 2
            banner_top = 0

            # Create shadow layer (offset by 3px)
            shadow_layer = Image.new("RGBA", badge_pil.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow_layer)
            shadow_offset = max(2, int(bw * 0.004))
            shadow_draw.rectangle(
                [(0, banner_top + shadow_offset), (bw, banner_top + banner_h + shadow_offset)],
                fill=(0, 0, 0, 100),
            )
            badge_pil = Image.alpha_composite(badge_pil, shadow_layer)

            # Create banner layer — solid deep indigo/violet background
            banner_layer = Image.new("RGBA", badge_pil.size, (0, 0, 0, 0))
            banner_draw = ImageDraw.Draw(banner_layer)
            # Deep indigo banner fill
            banner_draw.rectangle(
                [(0, banner_top), (bw, banner_top + banner_h)],
                fill=(30, 27, 75, 230),
            )
            # White bottom edge line for clean separation
            edge_h = max(2, int(bw * 0.003))
            banner_draw.rectangle(
                [(0, banner_top + banner_h - edge_h), (bw, banner_top + banner_h)],
                fill=(255, 255, 255, 200),
            )
            badge_pil = Image.alpha_composite(badge_pil, banner_layer)

            # Draw centered white text on the banner
            final_draw = ImageDraw.Draw(badge_pil)
            text_x = (bw - tw) // 2
            text_y = banner_top + pad_y - int(series_font_size * 0.05)
            # Small text shadow for readability
            final_draw.text((text_x + 1, text_y + 1), series_label, font=series_font, fill=(0, 0, 0, 120))
            final_draw.text((text_x, text_y), series_label, font=series_font, fill=(255, 255, 255, 255))

            # Save back as RGB
            badge_pil.convert("RGB").save(output_path, "JPEG", quality=75)
            logger.info(f"Added series banner '{series_label}' to cover page")

        return output_path

    @staticmethod
    def get_dominant_color(image_path, k=3):
        """
        Get the dominant color of an image using KMeans clustering.

        Parameters:
        image_path (str): Path to the input image
        k (int): Number of clusters for KMeans

        Returns:
        tuple: RGB values of the dominant color
        """
        # Remove file:// prefix if present for cv2
        clean_path = image_path.replace("file://", "")

        # Read the image
        image = cv2.imread(clean_path)
        if image is None:
            raise ValueError(f"Unable to read image at {clean_path}")

        # Reshape the image to a 2D array of pixels
        pixels = image.reshape(-1, 3)

        # Fit KMeans model
        kmeans = KMeans(n_clusters=k)
        kmeans.fit(pixels)

        # Get the dominant color
        dominant_color = kmeans.cluster_centers_[0]
        return tuple(int(val) for val in dominant_color)

    @staticmethod
    def validate_image_file(file_path: str) -> bool:
        """
        Validate that a file is a readable image using PIL.

        Opens the file with PIL and calls .verify() to check that the
        image data is not truncated or corrupt.  Returns True for a
        valid image, False otherwise.

        Parameters:
            file_path (str): Path to the image file (with or without file:// prefix)

        Returns:
            bool: True if the file is a valid image
        """
        clean_path = file_path.replace("file://", "")
        try:
            with Image.open(clean_path) as img:
                img.verify()  # checks headers + data integrity
            return True
        except Exception as e:
            logger.warning(f"Image validation failed for {clean_path}: {e}")
            return False

    @staticmethod
    @retry(
        exceptions=(Exception),
        max_retries=settings.DOWNLOAD_IMAGE_MAX_RETRIES,
        initial_delay=settings.DOWNLOAD_IMAGE_RETRY_DELAY,
        max_delay=settings.DOWNLOAD_IMAGE_MAX_DELAY,
        backoff_factor=3,
    )
    def download_image(url, temp_dir):
        """
        Download an image from a URL and save it to a local directory

        Parameters:
        url (str): URL of the image to download
        temp_dir (str): Directory to save the downloaded image

        Returns:
        str: Path to the downloaded image file with 'file://' prefix
        """
        try:
            # Create filename from URL
            parsed_url = urlparse(url)
            filename = os.path.basename(parsed_url.path)

            # Ensure filename is not empty
            if not filename:
                filename = f"image_{hash(url)}.jpg"

            # Full path to save the image
            local_path = os.path.join(temp_dir, filename)

            # Download the image
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for HTTP errors

            # Save the image to local path
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Validate the downloaded image is not corrupt
            if not ImageProcessor.validate_image_file(local_path):
                # Remove the corrupt file so the retry starts clean
                try:
                    os.remove(local_path)
                except OSError:
                    pass
                raise ValueError(
                    f"Downloaded image from {url} is corrupt or has unknown format"
                )

            # Return the local path with file:// prefix
            return f"file://{local_path}"

        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            raise ValueError(f"Failed to download image from {url}: {e}")

    @staticmethod
    def color_distance(color1, color2):
        """Calculate perceptual color distance using a modified CIEDE2000 approximation"""
        # Convert BGR to RGB if needed
        if len(color1) == 3:
            c1 = (color1[2], color1[1], color1[0])
            c2 = (color2[2], color2[1], color2[0])
        else:
            c1, c2 = color1, color2

        # Convert RGB to HSL (Hue, Saturation, Lightness)
        r1, g1, b1 = [x / 255 for x in c1]
        r2, g2, b2 = [x / 255 for x in c2]

        h1, l1, s1 = colorsys.rgb_to_hls(r1, g1, b1)
        h2, l2, s2 = colorsys.rgb_to_hls(r2, g2, b2)

        # Calculate distance based on lightness, saturation, and hue
        # Lightness difference is weighted more as it's crucial for readability
        lightness_diff = abs(l1 - l2) * 2.0
        saturation_diff = abs(s1 - s2)

        # Hue difference (handling circular nature of hue)
        hue_diff = min(abs(h1 - h2), 1 - abs(h1 - h2))

        # Combined distance (weighted sum)
        distance = lightness_diff * 0.6 + saturation_diff * 0.2 + hue_diff * 0.2

        return distance

    @staticmethod
    def are_colors_similar(color1, color2, threshold=0.5):
        """Check if two colors are too similar for good readability"""
        distance = ImageProcessor.color_distance(color1, color2)
        return distance < threshold

    @staticmethod
    def adjust_color_for_readability(base_color, color_to_adjust):
        """Adjust a color to improve readability against the base color"""
        # Convert BGR to RGB if needed
        if len(base_color) == 3:
            base = (base_color[2], base_color[1], base_color[0])
            adjust = (color_to_adjust[2], color_to_adjust[1], color_to_adjust[0])
        else:
            base, adjust = base_color, color_to_adjust

        # Convert to HSL
        r, g, b = [x / 255 for x in adjust]
        h, l, s = colorsys.rgb_to_hls(r, g, b)

        r_base, g_base, b_base = [x / 255 for x in base]
        h_base, l_base, s_base = colorsys.rgb_to_hls(r_base, g_base, b_base)

        # Primarily adjust lightness for readability
        if l_base > 0.5:
            # If base is light, make adjusted color darker
            l = max(0.1, l - 0.3)
        else:
            # If base is dark, make adjusted color lighter
            l = min(0.9, l + 0.3)

        # Convert back to RGB
        r_new, g_new, b_new = colorsys.hls_to_rgb(h, l, s)

        # Convert back to 0-255 range and BGR format if needed
        if len(base_color) == 3:
            adjusted_color = (
                int(b_new * 255),
                int(g_new * 255),
                int(r_new * 255),
            )  # BGR
        else:
            adjusted_color = (
                int(r_new * 255),
                int(g_new * 255),
                int(b_new * 255),
            )  # RGB

        return adjusted_color

    @staticmethod
    def get_optimized_text_stroke_colors(image_path, preloaded_image=None):
        """
        Get optimized stroke and text colors for readability from an image.

        Uses the average brightness of the image to pick white text on a dark
        stroke (for mid/light backgrounds) or black text on a white stroke
        (for dark backgrounds). This guarantees high contrast regardless of
        the image's color palette.

        Parameters:
        image_path (str): Path to the input image (with or without file:// prefix)
        preloaded_image: Optional pre-loaded cv2 image array to avoid re-reading from disk.

        Returns:
        dict: Dictionary containing optimized stroke_color and text_color as BGR tuples
        """
        if preloaded_image is not None:
            image = preloaded_image
        else:
            # Remove file:// prefix if present for cv2
            clean_path = image_path.replace("file://", "")
            image = cv2.imread(clean_path)
        if image is None:
            raise ValueError(f"Unable to read image at {image_path}")

        # Calculate average brightness of the image using standard luminance
        # (BGR channel order in OpenCV)
        avg_b, avg_g, avg_r = cv2.mean(image)[:3]
        brightness = avg_r * 0.299 + avg_g * 0.587 + avg_b * 0.114

        if brightness > 140:
            # Light/mid background → white text with dark stroke
            text_color = (255, 255, 255)  # White in BGR
            stroke_color = (30, 30, 30)   # Near-black in BGR
        else:
            # Dark background → black text with white stroke
            text_color = (0, 0, 0)        # Black in BGR
            stroke_color = (240, 240, 240) # Near-white in BGR

        return {
            "stroke_color": stroke_color,  # BGR format
            "text_color": text_color,  # BGR format
        }

    @staticmethod
    def add_logo_watermark(
        image_path,
        logo_path,
        opacity=0.3,
        scale_factor=0.15,
        position="center",
        repeat=True,
        diagonal=True,
    ):
        """
        Add a semi-transparent logo watermark to an image.

        Parameters:
        image_path (str): Path to the input image
        logo_path (str): Path to the logo image (preferably PNG with transparency)
        output_path (str): Path to save the output image
        opacity (float): Opacity of the watermark (0.0-1.0)
        scale_factor (float): Scale factor for logo size relative to the image size
        position (str or tuple): Position to place the logo ('center', 'topleft', etc.) or (x, y) coordinates
        repeat (bool): Whether to repeat the logo in a pattern across the image
        diagonal (bool): Whether to place logos in a diagonal pattern

        Returns:
        str: Path to the processed image
        """
        clean_image_path = image_path.replace("file://", "")
        clean_logo_path = logo_path.replace("file://", "")

        image = cv2.imread(clean_image_path)
        if image is None:
            raise ValueError(f"Unable to read image at {clean_image_path}")

        logo = cv2.imread(clean_logo_path, cv2.IMREAD_UNCHANGED)
        if logo is None:
            raise ValueError(f"Unable to read logo at {clean_logo_path}")

        # Handle logo with and without alpha channel
        if logo.shape[2] == 4:  # With alpha channel (BGRA)
            # Split the logo into color and alpha channels
            b, g, r, alpha = cv2.split(logo)
            logo_rgb = cv2.merge((b, g, r))

            # Normalize alpha channel to range 0-1
            alpha = alpha / 255.0
        else:  # Without alpha channel (BGR)
            logo_rgb = logo
            # Create a full opacity alpha channel
            alpha = np.ones((logo.shape[0], logo.shape[1]), dtype=np.float32)

        # Resize logo based on scale factor and main image size
        img_height, img_width = image.shape[:2]
        logo_width = int(img_width * scale_factor)

        # Calculate height while maintaining aspect ratio
        logo_aspect_ratio = logo_rgb.shape[1] / logo_rgb.shape[0]
        logo_height = int(logo_width / logo_aspect_ratio)

        # Resize logo and alpha channel
        logo_rgb = cv2.resize(logo_rgb, (logo_width, logo_height))
        alpha = cv2.resize(alpha, (logo_width, logo_height))

        # Create a transparent overlay the same size as the original image
        overlay = np.zeros_like(image, dtype=np.float32)

        # Define logo positions based on parameters
        positions = []

        if repeat:
            # Create a grid of positions for repeated logos
            horizontal_spacing = int(logo_width * 2)
            vertical_spacing = int(logo_height * 2)

            # Calculate how many logos to place horizontally and vertically
            cols = max(1, img_width // horizontal_spacing)
            rows = max(1, img_height // vertical_spacing)

            # Create offset to center the grid
            offset_x = (img_width - (cols * horizontal_spacing)) // 2
            offset_y = (img_height - (rows * vertical_spacing)) // 2

            # Create a diagonal or grid pattern
            for row in range(rows + 1):  # +1 to ensure coverage
                for col in range(cols + 1):  # +1 to ensure coverage
                    if diagonal:
                        # Staggered diagonal pattern
                        x = (
                            offset_x
                            + col * horizontal_spacing
                            + (row % 2) * (horizontal_spacing // 2)
                        )
                        y = offset_y + row * vertical_spacing
                    else:
                        # Regular grid pattern
                        x = offset_x + col * horizontal_spacing
                        y = offset_y + row * vertical_spacing

                    positions.append((x, y))
        else:
            if position == "center":
                x = (img_width - logo_width) // 2
                y = (img_height - logo_height) // 2
            elif position == "topleft":
                x, y = 10, 10
            elif position == "topright":
                x, y = img_width - logo_width - 10, 10
            elif position == "bottomleft":
                x, y = 10, img_height - logo_height - 10
            elif position == "bottomright":
                x, y = img_width - logo_width - 10, img_height - logo_height - 10
            elif isinstance(position, tuple) and len(position) == 2:
                x, y = position
            else:
                # Default to center
                x = (img_width - logo_width) // 2
                y = (img_height - logo_height) // 2

            positions.append((x, y))

        # Place logo(s) onto the overlay
        for x, y in positions:
            # Ensure logo placement is within image boundaries
            if (
                x < 0
                or y < 0
                or x + logo_width > img_width
                or y + logo_height > img_height
            ):
                continue

            # Get the region of interest in the overlay
            roi = overlay[y : y + logo_height, x : x + logo_width]

            # Apply the logo with alpha blending to the ROI
            for c in range(3):  # For each color channel
                roi[:, :, c] = alpha * logo_rgb[:, :, c] + (1 - alpha) * roi[:, :, c]

        # Blend the overlay with the original image based on opacity
        result = cv2.addWeighted(image, 1.0, overlay.astype(np.uint8), opacity, 0)

        cv2.imwrite(image_path, result, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        return image_path
