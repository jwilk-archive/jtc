int main()
{
  int x, y;
  for (x = 1; x < 5; x++)
    for (y = 1; y < 5; y++)
    {
      int z = -17;
      for (z = 1; z < 5; z++)
        printInt(x * y * z);
      printString("");
    }
  return 0;
}

/* vim:set ts=2 sts=2 sw=2 et ft=c: */
