# FLY-Screen
## Marlin 

firmware, you only need to set the baud rate to 115200 to communicate with the screen

## Duet reprap firmware

If you have turned on "Enable support for PanelDue", you need to modify the sys/config.g file M575 P1 S1 B57600 to M575 P1 S0 B57600

If you don’t enable it, just add M575 P1 S0 B57600 to sys/config.g

If you have any usage problems, please join https://discord.gg/hccjyvv Come to consult me

## upgrading firmware
只需将相应的update.img放入SD卡的根目录中，然后将其插入屏幕即可进行升级。
##  Boot display
If your screen is 4.3 inches, you need to create a 480*232 resolution picture, the picture size should not exceed 128kb, rename the picture name to boot_logo.JPG, JPG is uppercase. Put the picture into the root directory of the sd card, plug it into the screen to upgrade
7-inch screen: Create 800*480 resolution pictures, the others are the same as above.

## Other
# For Duet firmware:
Screen sd card, U disk, and firmware settings are temporarily unavailable, and will be supported in the near future
Project under development: modify the config.g file on the screen. Configure the machine firmware on the screen without opening the web page configuration
# For Marlin
Marlin's firmware settings try to enable M500, otherwise it may not be saved successfully.
## Feedback BUG
You can contact the seller on AliExpress, post on github, or contact me on discord. If you have any suggestions or inconvenient use, you can contact me. Will help you solve all problems usually within 24 hours
