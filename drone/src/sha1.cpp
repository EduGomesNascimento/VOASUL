#include "sha1.h"
#include <string.h>

static inline uint32_t rol(uint32_t v, uint32_t n) { return (v << n) | (v >> (32 - n)); }

static void sha1Block(uint32_t h[5], const uint8_t block[64]) {
  uint32_t w[80];
  for (int i = 0; i < 16; i++) {
    w[i] = ((uint32_t)block[i * 4] << 24) | ((uint32_t)block[i * 4 + 1] << 16) |
           ((uint32_t)block[i * 4 + 2] << 8) | (uint32_t)block[i * 4 + 3];
  }
  for (int i = 16; i < 80; i++) w[i] = rol(w[i - 3] ^ w[i - 8] ^ w[i - 14] ^ w[i - 16], 1);

  uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4];
  for (int i = 0; i < 80; i++) {
    uint32_t f, k;
    if (i < 20)      { f = (b & c) | (~b & d);            k = 0x5A827999; }
    else if (i < 40) { f = b ^ c ^ d;                     k = 0x6ED9EBA1; }
    else if (i < 60) { f = (b & c) | (b & d) | (c & d);   k = 0x8F1BBCDC; }
    else             { f = b ^ c ^ d;                     k = 0xCA62C1D6; }

    const uint32_t tmp = rol(a, 5) + f + e + k + w[i];
    e = d; d = c; c = rol(b, 30); b = a; a = tmp;
  }
  h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e;
}

void sha1(const uint8_t *data, size_t len, uint8_t out[20]) {
  uint32_t h[5] = {0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476, 0xC3D2E1F0};

  size_t full = len / 64;
  for (size_t i = 0; i < full; i++) sha1Block(h, data + i * 64);

  // Ultimo bloco: resto + bit 1 + zeros + comprimento em bits (64 bits, big endian)
  uint8_t tail[128];
  const size_t rest = len - full * 64;
  memcpy(tail, data + full * 64, rest);
  tail[rest] = 0x80;

  const size_t tailLen = (rest >= 56) ? 128 : 64;
  memset(tail + rest + 1, 0, tailLen - rest - 1);

  const uint64_t bits = (uint64_t)len * 8;
  for (int i = 0; i < 8; i++) tail[tailLen - 1 - i] = (uint8_t)(bits >> (8 * i));

  sha1Block(h, tail);
  if (tailLen == 128) sha1Block(h, tail + 64);

  for (int i = 0; i < 5; i++) {
    out[i * 4]     = (uint8_t)(h[i] >> 24);
    out[i * 4 + 1] = (uint8_t)(h[i] >> 16);
    out[i * 4 + 2] = (uint8_t)(h[i] >> 8);
    out[i * 4 + 3] = (uint8_t)(h[i]);
  }
}

void base64Encode(const uint8_t *data, size_t len, char *out, size_t outSize) {
  static const char T[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  const size_t need = 4 * ((len + 2) / 3) + 1;
  if (outSize < need) { if (outSize) out[0] = '\0'; return; }

  size_t o = 0;
  size_t i = 0;
  for (; i + 2 < len; i += 3) {
    const uint32_t v = ((uint32_t)data[i] << 16) | ((uint32_t)data[i + 1] << 8) | data[i + 2];
    out[o++] = T[(v >> 18) & 0x3F];
    out[o++] = T[(v >> 12) & 0x3F];
    out[o++] = T[(v >> 6) & 0x3F];
    out[o++] = T[v & 0x3F];
  }
  if (i < len) {
    uint32_t v = (uint32_t)data[i] << 16;
    const bool two = (i + 1 < len);
    if (two) v |= (uint32_t)data[i + 1] << 8;
    out[o++] = T[(v >> 18) & 0x3F];
    out[o++] = T[(v >> 12) & 0x3F];
    out[o++] = two ? T[(v >> 6) & 0x3F] : '=';
    out[o++] = '=';
  }
  out[o] = '\0';
}
