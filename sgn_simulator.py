#!/usr/bin/env python3
"""
Covert Pictorial Narrative and Multimedia Content Generation
in Image Communication Networks
==============================================================
GAN-inspired steganography framework for hiding pictorial narratives
in image communication channels with perceptual quality guarantees.

Methods implemented:
  1. LSB substitution (spatial domain baseline)
  2. DCT coefficient modulation (transform domain)
  3. GAN encoder-decoder (learned hiding)
  4. Adaptive pixel manipulation (just-noticeable-difference model)

Metrics: PSNR, SSIM (structural similarity), LPIPS proxy,
         MS-SSIM, bit accuracy, embedding capacity, detection rate
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import os, json, itertools, copy, warnings, sys, platform, subprocess, importlib.metadata
from scipy.signal import convolve2d
warnings.filterwarnings('ignore')

matplotlib.rcParams.update({
    'font.family': 'serif', 'font.size': 10,
    'axes.labelsize': 11, 'legend.fontsize': 8,
    'figure.dpi': 150,
})

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figures')
os.makedirs(OUTPUT_DIR, exist_ok=True)
SEED = 42
rng = np.random.default_rng(SEED)

# Image parameters
IMG_SIZE = 128            # pixels
N_CHANNELS = 3            # RGB
N_PIXELS = IMG_SIZE * IMG_SIZE * N_CHANNELS

# Steganography methods
METHODS = ['LSB', 'DCT', 'GAN_Enc', 'Adaptive_JND']

# ====================================================================
#  SYNTHETIC IMAGE GENERATOR
# ====================================================================

class ImageGenerator:
    """Generates synthetic images with controllable complexity for steganography tests."""
    def __init__(self, size=IMG_SIZE, seed=SEED):
        self.size = size
        self.rng = np.random.default_rng(seed)

    def generate(self, img_type='random', seed=None):
        """Generate a synthetic image of given type.

        Types: 'random', 'smooth', 'texture', 'edge_rich', 'natural_like'
        """
        s = self.size
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        rng = self.rng

        if img_type == 'random':
            return rng.integers(0, 256, (s, s, 3), dtype=np.uint8)

        elif img_type == 'smooth':
            base = rng.integers(60, 200, (1, 1, 3), dtype=np.float32)
            noise = rng.normal(0, 3, (s, s, 3)).astype(np.float32)
            img = np.clip(base + noise, 0, 255).astype(np.uint8)
            return img

        elif img_type == 'texture':
            img = np.zeros((s, s, 3), dtype=np.float32)
            for c in range(3):
                freq = rng.uniform(2, 20)
                phase = rng.uniform(0, 2*np.pi)
                for i in range(s):
                    for j in range(s):
                        val = 128 + 64 * np.sin(freq*(i+j)/s*2*np.pi + phase)
                        val += 32 * np.sin(freq*2*i/s*2*np.pi)
                        img[i, j, c] = val
            return np.clip(img, 0, 255).astype(np.uint8)

        elif img_type == 'edge_rich':
            img = rng.integers(30, 60, (s, s, 3), dtype=np.uint8)
            n_lines = rng.integers(10, 30)
            for _ in range(n_lines):
                direction = rng.choice(['h', 'v', 'd'])
                color = rng.integers(120, 255, 3, dtype=np.uint8)
                if direction == 'h':
                    row = rng.integers(0, s)
                    img[row, :] = color
                elif direction == 'v':
                    col = rng.integers(0, s)
                    img[:, col] = color
                else:
                    for k in range(s):
                        pos = int(k * rng.uniform(0.5, 1.5))
                        if pos < s:
                            img[k, pos] = color
            return img

        elif img_type == 'natural_like':
            img = np.zeros((s, s, 3), dtype=np.float32)
            for c in range(3):
                z = rng.normal(0, 1, (s, s)).astype(np.float32)
                # Smooth with Gaussian kernel
                ksize = 7
                kernel = np.outer(
                    np.exp(-np.arange(-ksize//2+1, ksize//2+1)**2 / (2*3**2)),
                    np.exp(-np.arange(-ksize//2+1, ksize//2+1)**2 / (2*3**2))
                )
                kernel /= kernel.sum()
                from scipy.signal import convolve2d
                z = convolve2d(z, kernel, mode='same', boundary='wrap')
                z = (z - z.min()) / (z.max() - z.min() + 1e-10)
                img[:, :, c] = z * 200 + 28
            return np.clip(img, 0, 255).astype(np.uint8)

    def generate_dataset(self, n=200, img_type='natural_like'):
        return [self.generate(img_type, seed=SEED+i) for i in range(n)]

# ====================================================================
#  STEGANOGRAPHY METHODS
# ====================================================================

class SteganographyBase:
    """Base class for steganography methods."""
    def __init__(self):
        self.name = 'Base'

    def encode(self, cover, secret_data):
        """Embed secret_data into cover image. Returns stego image."""
        raise NotImplementedError

    def decode(self, stego):
        """Extract secret data from stego image."""
        raise NotImplementedError

    def capacity(self):
        """Maximum bits that can be hidden per pixel."""
        raise NotImplementedError


class LSBSteganography(SteganographyBase):
    """Least Significant Bit substitution in spatial domain."""
    def __init__(self, bits_per_channel=1):
        super().__init__()
        self.name = 'LSB'
        self.bpc = bits_per_channel

    def encode(self, cover, secret_bits):
        """Embed bits into LSB planes."""
        mask = (1 << self.bpc) - 1
        flat = cover.copy().ravel()
        n_usable = len(flat) * self.bpc
        n_bits = min(len(secret_bits), n_usable)

        for i in range(n_bits):
            pi = i // self.bpc
            bi = i % self.bpc
            # Clear target bit, then set
            mask_bit = 255 ^ (1 << bi)
            flat[pi] = (flat[pi] & mask_bit) | (int(secret_bits[i]) << bi)

        return flat.reshape(cover.shape).astype(np.uint8), n_bits

    def decode(self, stego):
        """Extract LSB bits.

        Must be the inverse of `encode`: `encode` writes `bpc` bits per pixel
        into the low bits of each pixel value, so `decode` reads back `bpc`
        bits per pixel in the same order.

        The previous implementation masked each pixel and passed the result to
        `np.unpackbits`, which expands every uint8 into eight bits — seven
        structural zeros followed by the masked value. That returned
        `8 * len(flat)` bits where `encode` had written `bpc * len(flat)`, and
        placed the real bits at the end of each eight-bit group rather than at
        the position `encode` used. The consequence was that bit accuracy
        measured against a uniform-random payload sat at chance, and a payload of
        all zeros scored a perfect 1.0 for the wrong reason. See
        FALSIFIER-LOG.md for the pre-fix run that established the mechanism.
        """
        flat = stego.ravel()
        mask = (1 << self.bpc) - 1
        low = (flat & mask).astype(np.uint8)
        # `encode` writes bit `i` of a pixel into shift position `i % bpc`, so
        # the read order within a pixel is ascending shift position. The first
        # attempt here used descending order, which round-tripped correctly at
        # bpc=1 and failed at bpc=2 and bpc=3; the falsifier caught it.
        shifts = np.arange(self.bpc)
        bits = ((low[:, None] >> shifts[None, :]) & 1).astype(np.uint8)
        return bits.ravel()

    def capacity(self):
        return 3 * self.bpc  # bits per pixel


class DCTSteganography(SteganographyBase):
    """DCT-domain coefficient modulation (F5-like, fast block implementation)."""
    def __init__(self, quality=75):
        super().__init__()
        self.name = 'DCT'

    def _dct2_block(self, block):
        """Fast 2D DCT for 8x8 block using FFT."""
        M, N = block.shape
        # Type-II DCT via FFT
        a = np.zeros((M, N))
        for u in range(M):
            cu = np.sqrt(1/M) if u == 0 else np.sqrt(2/M)
            for v in range(N):
                cv = np.sqrt(1/N) if v == 0 else np.sqrt(2/N)
                s = 0.0
                for i in range(M):
                    for j in range(N):
                        s += block[i,j] * np.cos((2*i+1)*u*np.pi/(2*M)) * np.cos((2*j+1)*v*np.pi/(2*N))
                a[u,v] = cu * cv * s
        return a

    def _idct2_block(self, block):
        """Fast 2D inverse DCT."""
        M, N = block.shape
        a = np.zeros((M, N))
        for i in range(M):
            for j in range(N):
                s = 0.0
                for u in range(M):
                    cu = np.sqrt(1/M) if u == 0 else np.sqrt(2/M)
                    for v in range(N):
                        cv = np.sqrt(1/N) if v == 0 else np.sqrt(2/N)
                        s += cu * cv * block[u,v] * np.cos((2*i+1)*u*np.pi/(2*M)) * np.cos((2*j+1)*v*np.pi/(2*N))
                a[i,j] = s
        return a

    def encode(self, cover, secret_bits):
        """Embed in DCT mid-frequency coefficients."""
        h, w, c = cover.shape
        bits = list(secret_bits)
        bit_idx = 0

        # Mid-frequency coefficient positions
        mid_coeffs = [(3,1), (4,0), (2,2), (1,3), (0,4),
                      (5,0), (4,1), (3,2), (2,3), (1,4)]

        # Only process first few 8x8 blocks for speed
        n_blocks = min(16, h//8) * min(16, w//8)
        blocks_done = 0

        stego = cover.copy().astype(np.float32)

        for ch in range(c):
            for bi in range(0, min(h, 128)-7, 8):
                for bj in range(0, min(w, 128)-7, 8):
                    if blocks_done >= 20:  # limit blocks for speed
                        break
                    block = cover[bi:bi+8, bj:bj+8, ch].astype(np.float32) - 128
                    dct_block = self._dct2_block(block)

                    for u, v in mid_coeffs:
                        if bit_idx < len(bits):
                            coeff = dct_block[u, v]
                            quant = np.round(coeff / 16.0)
                            if int(abs(quant)) % 2 != bits[bit_idx]:
                                if quant > 0:
                                    quant += 1 if (quant % 2 == 0) else -1
                                else:
                                    quant -= 1 if (quant % 2 == 0) else -1
                            dct_block[u, v] = quant * 16.0
                            bit_idx += 1

                    block_out = self._idct2_block(dct_block) + 128
                    stego[bi:bi+8, bj:bj+8, ch] = block_out
                    blocks_done += 1

        return np.clip(np.round(stego), 0, 255).astype(np.uint8), bit_idx

    def decode(self, stego):
        h, w, c = stego.shape
        bits = []
        mid_coeffs = [(3,1), (4,0), (2,2), (1,3), (0,4),
                      (5,0), (4,1), (3,2), (2,3), (1,4)]
        blocks_done = 0
        for ch in range(c):
            for bi in range(0, min(h, 128)-7, 8):
                for bj in range(0, min(w, 128)-7, 8):
                    if blocks_done >= 20:
                        break
                    block = stego[bi:bi+8, bj:bj+8, ch].astype(np.float32) - 128
                    dct_block = self._dct2_block(block)
                    for u, v in mid_coeffs:
                        quant = np.round(dct_block[u, v] / 16.0)
                        bits.append(int(abs(quant)) % 2)
                        if len(bits) > 5000:
                            return np.array(bits[:5000])
                    blocks_done += 1
        return np.array(bits[:5000])

    def capacity(self):
        return 3 * ((IMG_SIZE//8)**2 * 10)  # ~3*16*16*10 = 7680 bits


class GANEncoderDecoder(SteganographyBase):
    """Learned encoder-decoder (simulated GAN hiding).
    
    Uses an autoencoder-like approach where:
      - Encoder: cover + secret → stego (learned perturbation)
      - Decoder: stego → secret (learned extraction)
    
    Simulated via SVD-based projection and inverse.
    """
    def __init__(self, latent_dim=64):
        super().__init__()
        self.name = 'GAN_Enc'
        self.latent_dim = latent_dim
        self.encoder_W = None
        self.decoder_W = None
        self.cover_mean = None

    def _patchify(self, img, patch_size=16):
        """Split image into patches."""
        h, w, c = img.shape
        ph, pw = h // patch_size, w // patch_size
        patches = img[:ph*patch_size, :pw*patch_size].reshape(
            ph, patch_size, pw, patch_size, c)
        patches = patches.transpose(0, 2, 1, 3, 4).reshape(ph*pw, -1)
        return patches, ph, pw

    def _depatchify(self, patches, ph, pw, patch_size=16, c=3):
        h, w = ph*patch_size, pw*patch_size
        img = patches.reshape(ph, pw, patch_size, patch_size, c)
        img = img.transpose(0, 2, 1, 3, 4).reshape(h, w, c)
        return img

    def fit(self, images):
        """Learn the encoder/decoder transforms from a set of cover images."""
        all_patches = []
        for img in images:
            patches, _, _ = self._patchify(img)
            all_patches.append(patches)
        X = np.concatenate(all_patches, axis=0).astype(np.float32)

        self.cover_mean = np.mean(X, axis=0)
        Xc = X - self.cover_mean

        # SVD to learn latent representation
        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
        k = min(self.latent_dim, Xc.shape[1])

        # Encoder: project to top-k components
        self.encoder_W = Vt[:k, :].T  # (D, k)
        # Decoder: reconstruct from latent
        self.decoder_W = Vt[:k, :]    # (k, D)
        return self

    def encode(self, cover, secret_bits):
        """Encode secret bits into cover using learned perturbation."""
        patches, ph, pw = self._patchify(cover)
        patches_f = patches.astype(np.float32)

        # Project to latent
        Xc = patches_f - self.cover_mean
        latent = Xc @ self.encoder_W

        # Modulate latent with secret bits
        n_bits = min(len(secret_bits), latent.size)
        bit_idx = 0
        for i in range(latent.shape[0]):
            for j in range(latent.shape[1]):
                if bit_idx < n_bits:
                    # Embed bit by perturbing latent coordinate
                    if secret_bits[bit_idx] == 1:
                        latent[i, j] += 0.1 * abs(latent[i, j]) + 0.01
                    else:
                        latent[i, j] -= 0.1 * abs(latent[i, j]) + 0.01
                    bit_idx += 1

        # Reconstruct
        patches_recon = latent @ self.decoder_W + self.cover_mean
        img_recon = self._depatchify(patches_recon, ph, pw)

        # Blend with original to limit distortion
        alpha = 0.3
        stego = ((1 - alpha) * cover.astype(np.float32) +
                  alpha * np.clip(img_recon, 0, 255))

        return np.clip(np.round(stego), 0, 255).astype(np.uint8), n_bits

    def decode(self, stego):
        """Extract bits by comparing with expected latent."""
        patches, ph, pw = self._patchify(stego)
        patches_f = patches.astype(np.float32)
        Xc = patches_f - self.cover_mean
        latent = Xc @ self.encoder_W

        # Extract bits from latent sign/magnitude
        bits = []
        for i in range(latent.shape[0]):
            for j in range(latent.shape[1]):
                bit = 1 if latent[i, j] > 0 else 0
                bits.append(bit)
                if len(bits) > 10000:
                    break
            if len(bits) > 10000:
                break
        return np.array(bits[:10000])

    def capacity(self):
        return self.latent_dim * ((IMG_SIZE // 16) ** 2)


class AdaptiveJNDSteganography(SteganographyBase):
    """Just-Noticeable Difference based adaptive embedding.
    
    Embeds more bits in textured/edge regions where human vision
    is less sensitive, fewer bits in smooth regions.
    """
    def __init__(self, max_bpc=3):
        super().__init__()
        self.name = 'Adaptive_JND'
        self.max_bpc = max_bpc

    def _jnd_map(self, img):
        """Compute JND (just-noticeable-difference) map."""
        gray = np.mean(img, axis=2).astype(np.float32)
        # Luminance masking
        bg = convolve2d(gray, np.ones((5,5))/25, mode='same', boundary='symm')
        jnd_lum = np.where(bg < 127, 17 * (1 - np.sqrt(bg/127)) + 3, 3/128 * (bg - 127) + 3)

        # Texture masking (using local variance)
        var = convolve2d(gray**2, np.ones((3,3))/9, mode='same', boundary='symm')
        var -= convolve2d(gray, np.ones((3,3))/9, mode='same', boundary='symm')**2
        jnd_tex = np.minimum(var / 10, 15)

        # Edge masking
        sobel_h = np.array([[-1,0,1],[-2,0,2],[-1,0,1]])
        sobel_v = np.array([[-1,-2,-1],[0,0,0],[1,2,1]])
        edge = np.abs(convolve2d(gray, sobel_h, mode='same', boundary='symm'))
        edge += np.abs(convolve2d(gray, sobel_v, mode='same', boundary='symm'))
        jnd_edge = np.minimum(edge / 20, 10)

        jnd = jnd_lum + jnd_tex + jnd_edge
        return jnd / 255.0  # normalized

    def encode(self, cover, secret_bits):
        """Adaptive embedding based on JND map (vectorized for speed)."""
        stego = cover.copy().astype(np.float32)
        jnd = self._jnd_map(cover)
        h, w, _ = cover.shape
        bit_idx = 0

        # Precompute scale map
        scale_map = np.maximum(1, (jnd * 16).astype(int))
        bits_per_pixel = np.maximum(1, np.minimum(self.max_bpc,
                                    (jnd * self.max_bpc + 1).astype(int)))

        for c in range(3):
            for i in range(h):
                for j in range(w):
                    if bit_idx >= len(secret_bits):
                        break
                    scale = int(scale_map[i, j])
                    n_bits = int(bits_per_pixel[i, j])
                    for b in range(n_bits):
                        if bit_idx >= len(secret_bits):
                            break
                        pix = int(stego[i, j, c])
                        target = (pix // (2 * scale)) * (2 * scale)
                        if secret_bits[bit_idx] == 1:
                            target += scale
                        stego[i, j, c] = target
                        bit_idx += 1

        return np.clip(np.round(stego), 0, 255).astype(np.uint8), bit_idx

    def decode(self, stego):
        """Extract bits using JND-based decoding (fast path: random sample)."""
        jnd = self._jnd_map(stego)
        h, w, _ = stego.shape
        bits = []

        # Use random pixel selection for speed
        n_pixels = min(10000, h * w)
        pixels = rng.choice(h * w, n_pixels, replace=False)
        for idx in pixels:
            i, j = idx // w, idx % w
            for c in range(3):
                scale = max(1, int(jnd[i, j] * 16))
                pix = int(stego[i, j, c])
                bit = (pix // scale) % 2
                bits.append(bit)
                if len(bits) > 5000:
                    return np.array(bits[:5000])
        return np.array(bits[:5000])

    def capacity(self):
        return self.max_bpc * N_PIXELS  # bits per image


# ====================================================================
#  METRICS
# ====================================================================

def psnr(original, stego):
    """Peak Signal-to-Noise Ratio in dB."""
    mse = np.mean((original.astype(np.float32) - stego.astype(np.float32))**2)
    if mse == 0:
        return 100.0
    return 20 * np.log10(255.0 / np.sqrt(mse))

def ssim(original, stego):
    """Structural Similarity Index (simplified single-scale)."""
    K1, K2 = 0.01, 0.03
    L = 255.0
    C1, C2 = (K1*L)**2, (K2*L)**2

    scores = []
    for c in range(3):
        x = original[:,:,c].astype(np.float32)
        y = stego[:,:,c].astype(np.float32)

        mu_x = np.mean(x)
        mu_y = np.mean(y)
        sigma_x = np.std(x)
        sigma_y = np.std(y)
        sigma_xy = np.mean((x - mu_x) * (y - mu_y))

        num = (2*mu_x*mu_y + C1) * (2*sigma_xy + C2)
        den = (mu_x**2 + mu_y**2 + C1) * (sigma_x**2 + sigma_y**2 + C2)
        scores.append(num / den)

    return np.mean(scores)

def ms_ssim(original, stego):
    """Multi-scale SSIM approximation (2 scales)."""
    s1 = ssim(original, stego)
    # Downsample 2x
    o2 = original[::2, ::2, :]
    s2 = ssim(o2, stego[::2, ::2, :])
    return 0.5 * s1 + 0.5 * s2

def lpips_proxy(original, stego):
    """Learned Perceptual Image Patch Similarity proxy.
    
    Uses a simple Laplacian pyramid-based distance as a no-reference proxy.
    Lower is more similar.
    """
    diff = 0
    img1 = original.astype(np.float32)
    img2 = stego.astype(np.float32)
    for scale in range(3):
        if scale > 0:
            img1 = img1[::2, ::2, :]
            img2 = img2[::2, ::2, :]
        # Laplacian filter
        lap = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]])
        for c in range(3):
            l1 = convolve2d(img1[:,:,c], lap, mode='same', boundary='symm')
            l2 = convolve2d(img2[:,:,c], lap, mode='same', boundary='symm')
            diff += np.mean((l1 - l2)**2)
    return diff / (255**2)  # normalize

def bit_accuracy(original_bits, extracted_bits, n):
    """Fraction of correctly extracted bits (first n bits)."""
    n = min(n, len(original_bits), len(extracted_bits))
    if n == 0:
        return 0.0
    return np.mean(original_bits[:n] == extracted_bits[:n])

def embedding_efficiency(original, stego, n_bits):
    """PSNR per embedded bit."""
    p = psnr(original, stego)
    if n_bits == 0:
        return float('inf')
    return p * n_bits / (IMG_SIZE * IMG_SIZE * 3)

# ====================================================================
#  STEGANALYSIS DETECTOR (for detection rate)
# ====================================================================

class SimpleSteganalysis:
    """Simple steganalysis detector using feature statistics.
    
    Higher score = more likely to be stego.
    """
    def __init__(self):
        self.threshold = None

    def _extract_features(self, img):
        """Statistical features for steganalysis."""
        feats = []
        gray = np.mean(img, axis=2).astype(np.float32)

        # Pixel value histogram statistics
        hist, _ = np.histogram(gray, bins=64, range=(0, 255))
        hist = hist / hist.sum()
        feats.extend([np.std(hist), np.max(hist), np.argmax(hist) / 64])

        # Adjacent pixel difference statistics
        diff_h = np.diff(gray, axis=1)
        diff_v = np.diff(gray, axis=0)
        for diff in [diff_h, diff_v]:
            feats.extend([np.mean(diff), np.std(diff),
                          np.max(np.abs(diff)),
                          np.percentile(np.abs(diff), 95)])

        # LSB plane correlation
        lsb = img & 1
        lsb_corr = np.mean(lsb[:,:,0] == lsb[:,:,1])
        feats.append(lsb_corr)

        # Block variance
        blocks = gray.reshape(IMG_SIZE//8, 8, IMG_SIZE//8, 8)
        block_var = np.std(np.std(blocks, axis=(1,3)))
        feats.append(block_var)

        return np.array(feats)

    def fit(self, cover_images, stego_images):
        """Train a simple threshold-based detector."""
        X = []
        y = []
        for img in cover_images:
            X.append(self._extract_features(img))
            y.append(0)
        for img in stego_images:
            X.append(self._extract_features(img))
            y.append(1)
        X = np.array(X)
        y = np.array(y)

        from sklearn.ensemble import RandomForestClassifier
        self.clf = RandomForestClassifier(n_estimators=50, random_state=SEED)
        self.clf.fit(X, y)
        return self

    def predict_proba(self, img):
        """Probability of being stego."""
        feats = self._extract_features(img).reshape(1, -1)
        return self.clf.predict_proba(feats)[0, 1]

# ====================================================================
#  SIMULATION
# ====================================================================

def generate_secret_message(n_bits):
    """Generate random secret message bits."""
    return rng.integers(0, 2, n_bits).astype(np.uint8)


def evaluate_method(method_name, cover, secret_bits, **kwargs):
    """Evaluate a steganography method on one image."""
    if method_name == 'LSB':
        stego = LSBSteganography(bits_per_channel=1)
    elif method_name == 'DCT':
        stego = DCTSteganography()
    elif method_name == 'GAN_Enc':
        stego = GANEncoderDecoder(latent_dim=64)
    elif method_name == 'Adaptive_JND':
        stego = AdaptiveJNDSteganography(max_bpc=3)
    else:
        raise ValueError(f"Unknown method: {method_name}")

    # For GAN_Enc, we need to fit the transform first
    if method_name == 'GAN_Enc':
        gen = ImageGenerator(seed=SEED)
        train_imgs = gen.generate_dataset(50, 'natural_like')
        stego.fit(train_imgs)

    stego_img, n_bits = stego.encode(cover, secret_bits)
    extracted = stego.decode(stego_img)

    p = psnr(cover, stego_img)
    s = ssim(cover, stego_img)
    ms = ms_ssim(cover, stego_img)
    lp = lpips_proxy(cover, stego_img)
    acc = bit_accuracy(secret_bits, extracted, n_bits)

    return {
        'method': method_name,
        'psnr': p,
        'ssim': s,
        'ms_ssim': ms,
        'lpips': lp,
        'bit_accuracy': acc,
        'n_bits_embedded': n_bits,
        'bpp': n_bits / (IMG_SIZE * IMG_SIZE * 3),
        'stego_img': stego_img,
    }


def capacity_distortion_tradeoff(methods=None, capacities=None):
    """Evaluate PSNR vs embedding capacity for each method."""
    if methods is None:
        methods = ['LSB', 'DCT', 'Adaptive_JND']
    if capacities is None:
        capacities = [0.1, 0.25, 0.5, 1.0, 2.0, 3.0]  # bpp

    gen = ImageGenerator(seed=SEED)
    cover = gen.generate('natural_like', seed=42)

    results = {}
    for method in methods:
        psnrs = []
        for cap in capacities:
            n_bits = int(cap * IMG_SIZE * IMG_SIZE * 3)
            bits = generate_secret_message(n_bits)

            if method == 'LSB':
                stego = LSBSteganography(bits_per_channel=max(1, int(cap)))
            elif method == 'DCT':
                stego = DCTSteganography()
            elif method == 'GAN_Enc':
                stego = GANEncoderDecoder(latent_dim=max(16, int(cap * 32)))
                train_imgs = gen.generate_dataset(30, 'natural_like')
                stego.fit(train_imgs)
            elif method == 'Adaptive_JND':
                stego = AdaptiveJNDSteganography(max_bpc=max(1, int(cap)))
            else:
                continue

            img, _ = stego.encode(cover, bits)
            psnrs.append(psnr(cover, img))
        results[method] = {'capacities': capacities, 'psnrs': psnrs}

    return results


def detection_resistance_test(methods=None, n_images=30):
    """Evaluate detection rate of steganalysis."""
    if methods is None:
        methods = ['LSB', 'DCT', 'GAN_Enc', 'Adaptive_JND']

    gen = ImageGenerator(seed=SEED)
    all_covers = gen.generate_dataset(n_images, 'natural_like')

    cover_feats = []
    stego_feats = {m: [] for m in methods}

    for method in methods:
        for i, cover in enumerate(all_covers):
            bits = generate_secret_message(5000)

            if method == 'LSB':
                stego = LSBSteganography(bits_per_channel=1)
            elif method == 'DCT':
                stego = DCTSteganography()
            elif method == 'GAN_Enc':
                stego = GANEncoderDecoder(latent_dim=64)
                train_imgs = gen.generate_dataset(30, 'natural_like')
                stego.fit(train_imgs)
            elif method == 'Adaptive_JND':
                stego = AdaptiveJNDSteganography(max_bpc=2)
            else:
                continue

            img, _ = stego.encode(cover, bits)
            stego_feats[method].append(img)

    return stego_feats, all_covers


# ====================================================================
#  PLOTS
# ====================================================================

def plot_example_images():
    """Show cover, stego, and difference for each method."""
    gen = ImageGenerator(seed=SEED)
    cover = gen.generate('natural_like', seed=42)
    bits = generate_secret_message(5000)

    fig, axes = plt.subplots(3, len(METHODS), figsize=(12, 8))

    for mi, method in enumerate(METHODS):
        res = evaluate_method(method, cover, bits)

        # Stego
        axes[0, mi].imshow(res['stego_img'])
        axes[0, mi].set_title(f'{method}\nPSNR={res["psnr"]:.1f}')
        axes[0, mi].axis('off')

        # Difference (amplified 10x)
        diff = np.abs(cover.astype(np.float32) - res['stego_img'].astype(np.float32))
        diff = np.clip(diff * 20, 0, 255).astype(np.uint8)
        axes[1, mi].imshow(diff, cmap='hot')
        axes[1, mi].set_title(f'Diff (20x)')
        axes[1, mi].axis('off')

        # Histogram of pixel differences
        flat_diff = diff.ravel()
        axes[2, mi].hist(flat_diff[flat_diff > 0], bins=20, color='coral', alpha=0.7)
        axes[2, mi].set_xlabel('Pixel diff')
        axes[2, mi].set_ylabel('Count')
        axes[2, mi].set_title(f'SSIM={res["ssim"]:.3f}')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_example_images.pdf'))
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_example_images.png'), dpi=150)
    plt.close()
    print("  [examples] saved.")


def plot_capacity_distortion(results):
    """Plot PSNR vs embedding capacity."""
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = {'LSB': 'gray', 'DCT': 'steelblue',
              'GAN_Enc': 'coral', 'Adaptive_JND': 'seagreen'}
    markers = {'LSB': 'o', 'DCT': 's', 'GAN_Enc': '^', 'Adaptive_JND': 'D'}

    for method, data in results.items():
        ax.plot(data['capacities'], data['psnrs'], 'o-',
                color=colors.get(method, 'blue'),
                marker=markers.get(method, 'o'),
                label=method, alpha=0.8, linewidth=2)

    ax.axhline(40, color='red', ls='--', alpha=0.4, label='PSNR=40 dB (good)')
    ax.axhline(30, color='orange', ls=':', alpha=0.4, label='PSNR=30 dB (fair)')
    ax.set_xlabel('Embedding Capacity (bpp)')
    ax.set_ylabel('PSNR (dB)')
    ax.set_title('Capacity vs Distortion Trade-off')
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_capacity_distortion.pdf'))
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_capacity_distortion.png'), dpi=150)
    plt.close()
    print("  [capacity] saved.")


def plot_metric_comparison():
    """Bar chart comparing all metrics across methods."""
    gen = ImageGenerator(seed=SEED)
    cover = gen.generate('natural_like', seed=42)
    bits = generate_secret_message(5000)

    metrics_names = ['PSNR', 'SSIM', 'MS-SSIM', 'Bit Acc.', 'BPP']
    method_colors = ['gray', 'steelblue', 'coral', 'seagreen']

    # Collect data
    data = {m: evaluate_method(m, cover, bits) for m in METHODS}

    fig, axes = plt.subplots(1, 5, figsize=(16, 4))

    metric_keys = ['psnr', 'ssim', 'ms_ssim', 'bit_accuracy', 'bpp']
    ylabels = ['PSNR (dB)', 'SSIM', 'MS-SSIM', 'Bit Accuracy', 'Bits/Pixel']
    ylims = [(0, 60), (0.7, 1.0), (0.7, 1.0), (0, 1), (0, 10)]

    for ax, mk, yl, yl2 in zip(axes, metric_keys, ylabels, ylims):
        vals = [data[m][mk] for m in METHODS]
        bars = ax.bar(METHODS, vals, color=method_colors, alpha=0.8,
                      edgecolor='k', linewidth=0.5)
        ax.set_ylabel(yl)
        ax.set_ylim(yl2)
        ax.tick_params(axis='x', rotation=20)
        ax.grid(axis='y', alpha=0.3)
        # Add values on bars
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{v:.3f}', ha='center', va='bottom', fontsize=7)

    plt.suptitle('Steganography Method Comparison (5000 bits, 128x128 image)',
                 fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_metric_comparison.pdf'))
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_metric_comparison.png'), dpi=150)
    plt.close()
    print("  [metrics] saved.")


def plot_jnd_map():
    """Visualize JND map for adaptive embedding."""
    gen = ImageGenerator(seed=SEED)
    cover = gen.generate('natural_like', seed=42)

    from scipy.signal import convolve2d
    gray = np.mean(cover, axis=2).astype(np.float32)
    bg = convolve2d(gray, np.ones((5,5))/25, mode='same', boundary='symm')
    jnd_lum = np.where(bg < 127, 17 * (1 - np.sqrt(bg/127)) + 3, 3/128 * (bg - 127) + 3)
    var = convolve2d(gray**2, np.ones((3,3))/9, mode='same', boundary='symm')
    var -= convolve2d(gray, np.ones((3,3))/9, mode='same', boundary='symm')**2
    jnd_tex = np.minimum(var / 10, 15)
    jnd = jnd_lum + jnd_tex

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    axes[0].imshow(cover)
    axes[0].set_title('Original Image')
    axes[0].axis('off')

    im1 = axes[1].imshow(jnd_lum, cmap='hot')
    axes[1].set_title('Luminance JND')
    axes[1].axis('off')
    plt.colorbar(im1, ax=axes[1])

    im2 = axes[2].imshow(jnd, cmap='hot')
    axes[2].set_title('Combined JND Map\n(darker = more hiding capacity)')
    axes[2].axis('off')
    plt.colorbar(im2, ax=axes[2])

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_jnd_map.pdf'))
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_jnd_map.png'), dpi=150)
    plt.close()
    print("  [JND] saved.")


def plot_detection_rate(stego_dict, covers):
    """Steganalysis detection rate for each method."""
    methods = list(stego_dict.keys())
    detection_rates = []

    for method in methods:
        stegos = stego_dict[method]
        X = []
        y = []
        for img in covers:
            X.append(np.mean(img.astype(np.float32), axis=2).ravel())
            y.append(0)
        for img in stegos:
            X.append(np.mean(img.astype(np.float32), axis=2).ravel())
            y.append(1)
        X = np.array([x[:1024] for x in X])  # use only first 32x32 patch
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import cross_val_score
        clf = RandomForestClassifier(n_estimators=30, random_state=SEED)
        scores = cross_val_score(clf, X, y, cv=5)
        detection_rates.append(np.mean(scores))

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ['gray', 'steelblue', 'coral', 'seagreen'][:len(methods)]
    bars = ax.bar(methods, detection_rates, color=colors, alpha=0.8,
                  edgecolor='k', linewidth=0.5)
    for bar, v in zip(bars, detection_rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{v:.3f}', ha='center', fontsize=9)
    ax.axhline(0.5, color='red', ls='--', alpha=0.4, label='Random guess')
    ax.set_ylabel('Detection Rate')
    ax.set_title('Steganalysis Detection Rate (5-fold CV)')
    ax.legend(fontsize=8)
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, 1)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_detection_rate.pdf'))
    plt.savefig(os.path.join(OUTPUT_DIR, 'fig_detection_rate.png'), dpi=150)
    plt.close()
    print("  [detection] saved.")
    return {m: float(r) for m, r in zip(methods, detection_rates)}


# ====================================================================
#  MAIN
# ====================================================================
def _source_revision():
    """The revision and cleanliness of the checkout that produced the run.

    This is provenance, not identity. A run from a dirty tree is still a real
    run and must not be reported as if it came from the recorded revision, so
    the dirtiness is recorded rather than resolved.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    def git(*args):
        try:
            out = subprocess.run(['git', '-C', here, *args],
                                 capture_output=True, text=True)
        except OSError:
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    commit = git('rev-parse', 'HEAD')
    status = git('status', '--porcelain')
    dirty = bool(status) if status is not None else None
    return commit, dirty


def _dependency_versions():
    """Installed distributions this run's numbers could depend on.

    Read from installed metadata rather than imported modules, because scipy
    and scikit-learn are imported lazily inside the functions that use them, and
    their absence must be reported as absent rather than assumed.
    """
    versions = {}
    for name in ('numpy', 'scipy', 'matplotlib', 'scikit-learn'):
        try:
            versions[name] = importlib.metadata.version(name)
        except Exception:
            versions[name] = 'absent'
    return versions


def execution_provenance(configuration):
    """Provenance sufficient to distinguish this run from another.

    Row 6c. The artifact already carried its numbers and its seed; what it
    could not answer was which code and which environment produced them. That
    gap is invisible while the checkout is unchanged and permanent afterwards,
    because a deterministic run under a different revision or a different
    scikit-learn is not the same run.
    """
    commit, dirty = _source_revision()
    return {
        'source_commit': commit,
        'source_dirty': dirty,
        'python_version': '{}.{}.{}'.format(*sys.version_info[:3]),
        'python_implementation': platform.python_implementation(),
        'dependency_versions': _dependency_versions(),
        'platform': platform.system(),
        'architecture': platform.machine(),
        'seed': SEED,
        'configuration': configuration,
        'generator': 'sgn_simulator.py main()',
    }


def main():
    print("="*65)
    print("  Covert Pictorial Narrative and Multimedia Content")
    print("  Generation in Image Communication Networks")
    print("="*65)

    print(f"\n  Image size: {IMG_SIZE}x{IMG_SIZE}x{N_CHANNELS}")
    print(f"  Methods: {', '.join(METHODS)}")

    # Example images
    print("\n[Example Images]")
    plot_example_images()

    # JND visualization
    print("\n[JND Map]")
    plot_jnd_map()

    # Metric comparison
    print("\n[Metric Comparison]")
    plot_metric_comparison()

    # Capacity vs distortion
    print("\n[Capacity-Distortion Trade-off]")
    results = capacity_distortion_tradeoff()
    plot_capacity_distortion(results)

    # Detection resistance
    print("\n[Detection Rate Analysis]")
    stego_dict, covers = detection_resistance_test(n_images=10)
    detection = plot_detection_rate(stego_dict, covers)

    # Summary
    print(f"\n{'='*65}")
    print("  RESULTS SUMMARY")
    print(f"{'='*65}")
    gen = ImageGenerator(seed=SEED)
    cover = gen.generate('natural_like', seed=42)
    bits = generate_secret_message(5000)
    print(f"  {'Method':<18} {'PSNR':<8} {'SSIM':<8} {'BPP':<8} {'BitAcc':<8}")
    print("  " + "-"*50)
    summary = {}
    for method in METHODS:
        res = evaluate_method(method, cover, bits)
        print(f"  {method:<18} {res['psnr']:<8.2f} {res['ssim']:<8.4f} "
              f"{res['bpp']:<8.4f} {res['bit_accuracy']:<8.4f}")
        summary[method] = {
            'psnr_db': round(float(res['psnr']), 4),
            'ssim': round(float(res['ssim']), 6),
            'bpp': round(float(res['bpp']), 4),
            'bit_accuracy': round(float(res['bit_accuracy']), 6),
            'n_bits_embedded': int(res['n_bits_embedded']),
        }

    # Save.
    #
    # Row 6b: this artifact previously held only {'methods': [...]}, so no
    # published value in this repository was derivable from it. It now carries
    # the numbers the summary above actually computed, and tools/
    # reconcile_readme.py renders the published table from it. tests/
    # test_provenance.py asserts the published table equals that rendering, so a
    # hand-edited value is detected. See FALSIFIER-LOG-6b.md.
    artifact = {
        'schema': 'sgn-metrics/1',
        'provenance': execution_provenance({
            'cover': 'natural_like, seed=42',
            'payload_bits': int(len(bits)),
            'image_shape': [IMG_SIZE, IMG_SIZE, N_CHANNELS],
        }),
        'methods': METHODS,
        'detection': detection,
        'summary': summary,
    }
    json.dump(artifact,
              open(os.path.join(OUTPUT_DIR, 'metrics.json'), 'w'), indent=2)
    print(f"\n  Figures saved to {OUTPUT_DIR}/")
    print("  Done.")


if __name__ == '__main__':
    main()
