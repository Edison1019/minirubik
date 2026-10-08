/* Minimal Ripes environment-call adapter; no search logic is changed. */
#include <stdarg.h>
#include <stddef.h>
#include "ripes_stdio/stdio.h"

extern int solver_reference_main(int, char **);
const char input_str[] = "21345671111111";

static void print_string(const char *text)
{
    register const char *arg0 __asm__("a0") = text;
    register int service __asm__("a7") = 4;
    __asm__ volatile("ecall" : "+r"(arg0) : "r"(service) : "memory");
}

int fputs(const char *text, FILE *stream)
{
    (void)stream;
    print_string(text);
    return 0;
}

int printf(const char *format, ...)
{
    va_list args;
    va_start(args, format);
    /* solver.c's only printf format is "%s%s". */
    if (format[0] != '%' || format[1] != 's' || format[2] != '%' ||
        format[3] != 's' || format[4] != 0) {
        va_end(args);
        return EOF;
    }
    print_string(va_arg(args, const char *));
    print_string(va_arg(args, const char *));
    va_end(args);
    return 0;
}

int putchar(int c)
{
    char text[2] = {(char)c, 0};
    print_string(text);
    return c;
}

size_t fwrite(const void *buffer, size_t size, size_t count, FILE *stream)
{
    (void)stream;
    const unsigned char *bytes = buffer;
    for (size_t item = 0; item < count; ++item)
        for (size_t i = 0; i < size; ++i) putchar(*bytes++);
    return count;
}

int fflush(FILE *stream) { (void)stream; return 0; }
int ferror(FILE *stream) { (void)stream; return 0; }

void *memcpy(void *destination, const void *source, size_t count)
{
    unsigned char *d = destination;
    const unsigned char *s = source;
    for (size_t i = 0; i < count; ++i) d[i] = s[i];
    return destination;
}

void *memset(void *destination, int value, size_t count)
{
    unsigned char *d = destination;
    for (size_t i = 0; i < count; ++i) d[i] = (unsigned char)value;
    return destination;
}

int reference_entry(void)
{
    char *argv[] = {"solver", (char *)input_str};
    return solver_reference_main(2, argv);
}
