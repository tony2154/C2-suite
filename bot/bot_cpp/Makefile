# Makefile para ShadowC2 Bot C++
CXX = g++
CXXFLAGS = -std=c++17 -O2 -Wall -fPIC
LDFLAGS = -lcurl -lssl -lcrypto -ljsoncpp -lpthread -lX11 -lXtst

TARGET = bot_cpp
SRCS = main.cpp crypto.cpp network.cpp system_info.cpp keylogger.cpp persistence.cpp
OBJS = $(SRCS:.cpp=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(OBJS) -o $(TARGET) $(LDFLAGS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)

install: $(TARGET)
	cp $(TARGET) /usr/local/bin/shadow-update
	chmod +x /usr/local/bin/shadow-update

.PHONY: all clean install
