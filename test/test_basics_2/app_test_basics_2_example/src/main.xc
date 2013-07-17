#include <print.h>
#include "module.h"

#define APP_MAJOR_VERSION 0
#define APP_MINOR_VERSION 0
#define APP_POINT_VERSION 0
#define APP_MAJOR_VERSION_STR "0"
#define APP_MINOR_VERSION_STR "0"
#define APP_POINT_VERSION_STR "0"
#define APP_FULL_VERSION_STR  "0.0.0"
#define APP_VERSION_STR  "0.0.0"

int main()
{
    int x = APP_MAJOR_VERSION;
    x = module_test(x);
    printintln(APP_MAJOR_VERSION);
    printintln(APP_MINOR_VERSION);
    printintln(APP_POINT_VERSION);
    printstrln(APP_MAJOR_VERSION_STR);
    printstrln(APP_MINOR_VERSION_STR);
    printstrln(APP_POINT_VERSION_STR);
    printstrln(APP_FULL_VERSION_STR);
    printstrln(APP_VERSION_STR);
    return 0;
}
