int clasificar(int x, unsigned u)
{
    if (x > 5)
        return 1;
    if (x == 0 || u < 3u)
        return 2;
    while (x != 10)
        x++;
    return 0;
}
