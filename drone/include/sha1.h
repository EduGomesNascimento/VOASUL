#pragma once
#include <stddef.h>
#include <stdint.h>

// SHA-1 e base64, o minimo necessario para o aperto de mao do WebSocket.
// Escritos aqui porque ESP32 e RP2040 expoem bibliotecas de cripto diferentes,
// e sao ~80 linhas que valem mais do que uma dependencia condicional.

void sha1(const uint8_t *data, size_t len, uint8_t out[20]);

// Escreve base64 de len bytes em out (com terminador). Precisa de
// 4*ceil(len/3)+1 bytes.
void base64Encode(const uint8_t *data, size_t len, char *out, size_t outSize);
