#ifndef RIPES_REFERENCE_STDIO_H
#define RIPES_REFERENCE_STDIO_H
typedef struct { int unused; } FILE;
#define stdout ((FILE *)1)
#define stderr ((FILE *)2)
#define EOF (-1)
#ifndef NULL
#define NULL ((void *)0)
#endif
int printf(const char *, ...);
int fputs(const char *, FILE *);
int putchar(int);
int fflush(FILE *);
int ferror(FILE *);
#endif
