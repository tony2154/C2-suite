obj-m += shadow_rootkit.o

all:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules

clean:
	make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean

load:
	sudo insmod shadow_rootkit.ko

unload:
	sudo rmmod shadow_rootkit

test:
	sudo dmesg -C
	sudo insmod shadow_rootkit.ko
	lsmod | grep shadow
	sudo rmmod shadow_rootkit
	sudo dmesg
