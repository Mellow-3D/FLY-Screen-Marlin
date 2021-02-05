# FLY-Screen

## Marlin 

firmware, you only need to set the baud rate to 115200 to communicate with the screen
```
#define BAUDRATE 115200
```
STM32 motherboards usually need to be set
```
 #define SERIAL_PORT_2 1
 ```
LPC motherboards usually need to be set
```
 #define SERIAL_PORT_2 0
```

## Duet reprap firmware

Please find the firmware in the [fly-screen-reprap repository](https://github.com/FLYmaker/FLY-Screen-RepRap)

## upgrading firmware
只需将相应的update.img放入SD卡的根目录中，然后将其插入屏幕即可进行升级。
##  Boot display
If your screen is 4.3 inches, you need to create a 480*232 resolution picture, the picture size should not exceed 128kb, rename the picture name to boot_logo.JPG, JPG is uppercase. Put the picture into the root directory of the sd card, plug it into the screen to upgrade
7-inch screen: Create 800*480 resolution pictures, the others are the same as above.

# For Marlin
Marlin's firmware settings try to enable M500, otherwise it may not be saved successfully.

## Feedback BUG
You can contact the seller on AliExpress, post on github, or contact me on discord. If you have any suggestions or inconvenient use, you can contact me. Will help you solve all problems usually within 24 hours

## Support

If you have any usage problems, please join https://discord.gg/hccjyvv Come to consult me