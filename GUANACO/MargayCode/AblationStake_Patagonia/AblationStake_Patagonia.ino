#include "Margay.h"
#include <MaxbotixAW.h>
#include <T9602.h>

Margay Logger(Model_2v0, Build_B);

// 6
// Hard-coded for RX1
Maxbotix Range;

// 7
T9602 TRH;  //Initialize T9602 Humidity sensor


String Header = ""; //Information header

//0x28: T9602 (T, RH)
uint8_t I2CVals[] = {0x28};
unsigned long UpdateRate = 300; //Number of seconds between readings 

void setup() {
        Header = TRH.GetHeader() + \
                 Range.GetHeader();
                 
        Logger.begin(I2CVals, sizeof(I2CVals), Header); // Pass header info 
                                                        // to logger
        Init();
}

void loop() {
        Init(); //Ensure devices are intialized after power cycle 
        Logger.Run(Update, UpdateRate);
}

String Update() {
        return TRH.GetString() + Range.GetString();
}

void Init()
{
        Range.begin();
        TRH.begin();
}
