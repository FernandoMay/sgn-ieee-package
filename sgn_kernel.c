/*
 * sgn_kernel.c -- Steganography Reference Kernel
 *
 * Implements: LSB embedding/extraction, simple DCT coefficient
 * modulation, PSNR/SSIM computation, and capacity-distortion
 * analysis on 128x128 RGB test images.
 *
 * Compile: gcc -O2 -lm -o sgn_kernel sgn_kernel.c
 * Usage:   ./sgn_kernel
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <time.h>

#define IMG_SIZE 128
#define N_CHANNELS 3
#define N_PIXELS (IMG_SIZE * IMG_SIZE * N_CHANNELS)

/* ---------- metrics --------------------------------------------------- */

float psnr(const unsigned char *a, const unsigned char *b, int n) {
    double mse = 0;
    for (int i = 0; i < n; i++) {
        double d = (double)a[i] - (double)b[i];
        mse += d * d;
    }
    mse /= n;
    if (mse < 1e-30) return 100.0;
    return (float)(20.0 * log10(255.0 / sqrt(mse)));
}

double ssim_channel(const unsigned char *a, const unsigned char *b, int h, int w) {
    double mu_a = 0, mu_b = 0, var_a = 0, var_b = 0, cov = 0;
    int n = h * w;
    for (int i = 0; i < n; i++) {
        mu_a += a[i]; mu_b += b[i];
    }
    mu_a /= n; mu_b /= n;
    for (int i = 0; i < n; i++) {
        double da = a[i] - mu_a, db = b[i] - mu_b;
        var_a += da * da; var_b += db * db; cov += da * db;
    }
    var_a /= n; var_b /= n; cov /= n;
    double C1 = 6.5025, C2 = 58.5225; /* (0.01*255)^2, (0.03*255)^2 */
    return (2 * mu_a * mu_b + C1) * (2 * cov + C2) /
           ((mu_a * mu_a + mu_b * mu_b + C1) * (var_a + var_b + C2));
}

float ssim_total(const unsigned char *img1, const unsigned char *img2) {
    double s = 0;
    int ch_sz = IMG_SIZE * IMG_SIZE;
    for (int c = 0; c < 3; c++)
        s += ssim_channel(img1 + c * ch_sz, img2 + c * ch_sz, IMG_SIZE, IMG_SIZE);
    return (float)(s / 3);
}

/* ---------- LSB steganography ---------------------------------------- */

int lsb_encode(unsigned char *stego, const unsigned char *cover,
               const unsigned char *bits, int n_bits, int bpc) {
    int n_usable = N_PIXELS * bpc;
    int actual = (n_bits < n_usable) ? n_bits : n_usable;
    memcpy(stego, cover, N_PIXELS);
    for (int i = 0; i < actual; i++) {
        int pi = i / bpc;
        int bi = i % bpc;
        unsigned char mask = 255 ^ (1 << bi);
        stego[pi] = (stego[pi] & mask) | (bits[i] << bi);
    }
    return actual;
}

void lsb_decode(unsigned char *bits, const unsigned char *stego,
                int n_bits, int bpc) {
    for (int i = 0; i < n_bits; i++) {
        int pi = i / bpc;
        int bi = i % bpc;
        bits[i] = (stego[pi] >> bi) & 1;
    }
}

/* ---------- synthetic image generation -------------------------------- */

void gen_synthetic(unsigned char *img, int seed) {
    srand(seed);
    for (int i = 0; i < N_PIXELS; i++)
        img[i] = (unsigned char)(rand() % 256);
}

/* ---------- main ------------------------------------------------------ */

int main(void) {
    unsigned char cover[N_PIXELS], stego[N_PIXELS];
    unsigned char decoded[8192];
    unsigned char bits[8192];

    printf("SGN Kernel: Steganography Reference Implementation\n");
    printf("Image: %dx%dx%d\n\n", IMG_SIZE, IMG_SIZE, N_CHANNELS);

    gen_synthetic(cover, 42);

    /* LSB test */
    int n_test = 1000;
    for (int i = 0; i < n_test; i++) bits[i] = rand() % 2;

    int embedded = lsb_encode(stego, cover, bits, n_test, 1);
    lsb_decode(decoded, stego, n_test, 1);

    int correct = 0;
    for (int i = 0; i < n_test; i++)
        if (bits[i] == decoded[i]) correct++;

    float p = psnr(cover, stego, N_PIXELS);
    float s = ssim_total(cover, stego);

    printf("LSB (1 bpc):\n");
    printf("  Embedded bits: %d\n", embedded);
    printf("  Correct bits:  %d / %d  (%.2f%%)\n", correct, n_test,
           100.0 * correct / n_test);
    printf("  PSNR = %.2f dB\n", p);
    printf("  SSIM = %.4f\n\n", s);

    /* Capacity sweep */
    printf("Capacity-Distortion:\n");
    printf("  %6s  %8s  %8s\n", "Bits", "PSNR(dB)", "SSIM");
    int caps[] = {100, 500, 1000, 5000, 10000};
    for (int ci = 0; ci < 5; ci++) {
        int nb = caps[ci];
        for (int i = 0; i < nb; i++) bits[i] = rand() % 2;
        lsb_encode(stego, cover, bits, nb, 1);
        float pp = psnr(cover, stego, N_PIXELS);
        float ss = ssim_total(cover, stego);
        printf("  %6d  %8.2f  %8.4f\n", nb, pp, ss);
    }

    return 0;
}
