int main()
{
  printInt(+32 % -10);
  printInt(-32 % -10);
  printInt(+32 % +10);
  printInt(-32 % +10);
  printString("");
  printInt(+38 % -10);
  printInt(-38 % -10);
  printInt(+38 % +10);
  printInt(-38 % +10);
  printString("");
  printDouble(+32.0 % -10.0);
  printDouble(-32.0 % -10.0);
  printDouble(+32.0 % +10.0);
  printDouble(-32.0 % +10.0);
  printString("");
  printDouble(+38.0 % -10.0);
  printDouble(-38.0 % -10.0);
  printDouble(+38.0 % +10.0);
  printDouble(-38.0 % +10.0);
  return 0;
}

/* vim:set ts=2 sts=2 sw=2 et ft=c: */
