# Testes da logica dos gestos, no PC:  make
CXX ?= g++
test: test_gestos.cpp ../include/gestos.h
	$(CXX) -std=gnu++17 -O1 -Wall -Wextra -I../include -o gestos_bin test_gestos.cpp
	./gestos_bin
clean:
	rm -f gestos_bin
