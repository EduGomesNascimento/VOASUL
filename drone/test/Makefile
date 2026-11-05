# Testes de logica rodando no PC, sem placa e sem PlatformIO.
#
#   cd drone/test && make          # roda os testes
#   cd drone/test && make syntax   # checa o firmware inteiro das duas placas
#
# Verificam o que nao da para conferir olhando: convencoes de sinal do AHRS, do
# mixer e do desvio, fiacao do driver de motor, anti-windup do PID, fusao de
# altitude, fluxo optico, SHA-1 e o enquadramento do WebSocket.
# Rode sempre que mexer em ganhos, em pinos ou em qualquer sinal.

CXX      ?= g++
CXXFLAGS := -std=gnu++17 -O1 -Wall -Wextra -Wno-unused-parameter \
            -I../include -Istubs

SRC := tests.cpp stubs/stubs.cpp \
       ../src/ahrs.cpp ../src/pid.cpp ../src/motors.cpp \
       ../src/altitude.cpp ../src/avoidance.cpp ../src/rangefinder.cpp \
       ../src/sha1.cpp ../src/websocket.cpp ../src/platform.cpp \
       ../src/opticalflow.cpp

# Arquivos que dependem do WiFi da placa nao entram na compilacao do host;
# para eles vale a checagem cruzada de sintaxe abaixo.
SYNTAX_SRC := ../src/bmi160.cpp ../src/bmp280.cpp ../src/ahrs.cpp ../src/pid.cpp \
              ../src/motors.cpp ../src/rangefinder.cpp ../src/altitude.cpp \
              ../src/avoidance.cpp ../src/battery.cpp ../src/sha1.cpp \
              ../src/websocket.cpp ../src/platform.cpp ../src/opticalflow.cpp ../src/main.cpp

.PHONY: all check syntax flowhw clean
all: check

check: tests flowhw
	./tests

# driver do PMW3901 (fluxo optico) contra um sensor simulado em stubs/SPI.h
flowhw: flowhw.cpp ../src/opticalflow.cpp stubs/stubs.cpp stubs/SPI.h
	$(CXX) $(CXXFLAGS) -DFLOW_HW_TEST -DPIN_FLOW_CS=26 -DPIN_FLOW_SCK=33 \
	  -DPIN_FLOW_MOSI=25 -DPIN_FLOW_MISO=32 -o flowhw_bin flowhw.cpp ../src/opticalflow.cpp stubs/stubs.cpp
	./flowhw_bin

tests: $(SRC)
	$(CXX) $(CXXFLAGS) -o $@ $(SRC)

syntax:
	$(CXX) $(CXXFLAGS) -fsyntax-only $(SYNTAX_SRC)
	@echo "sintaxe ok"

clean:
	rm -f tests flowhw_bin
