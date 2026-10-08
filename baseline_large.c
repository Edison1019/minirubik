#define SIZE (4 * 1024 * 1024)

volatile unsigned char buffer[SIZE];

int main(void)
{
    for (int i = 0; i < SIZE; i++) {
        buffer[i] = (unsigned char)i;
    }

    return 0;
}