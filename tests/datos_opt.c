#include <stddef.h>

static int cuadrado(int x)
{
    return x * x;
}

int suma_cuadrados(const int *v, size_t n)
{
    int s = 0;
    for (size_t i = 0; i < n; i++)
    {
        s += cuadrado(v[i]);
    }
    return s;
}

int maximo(int a, int b)
{
    if (a > b)
        return a;
    return b;
}

int mcd(int a, int b)
{
    if (b == 0)
        return a;
    return mcd(b, a % b);
}

int suma_hasta_diez(void)
{
    int s = 0;
    for (int i = 1; i <= 10; i++)
        s += i;
    return s;
}

const char *dia(int d)
{
    if (d == 1) return "lunes";
    else if (d == 2) return "martes";
    else if (d == 3) return "miércoles";
    else if (d == 4) return "jueves";
    else if (d == 5) return "viernes";
    else if (d == 6) return "sábado";
    else return "domingo";
}

int puntos(int carta)
{
    if (carta == 1) return 11;
    else if (carta == 10) return 4;
    else if (carta == 12) return 3;
    else if (carta == 300) return 2;
    else if (carta == -7) return 10;
    return 0;
}
