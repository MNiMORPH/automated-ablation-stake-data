#include <SdFat.h>
#include <Wire.h>
#include <DS3231.h>
#include <math.h>
#include <avr/sleep.h>
//#include <avr/power.h>

// From weather station code
// http://jeelabs.net/projects/11/wiki/Weather_station_code
// Commented because using easier built-in functions
// --> Uncommented: this works better / more reliably than I can get
//     the AVR power functions to be without really digging into them.
#ifndef cbi
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#endif
#ifndef sbi
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))
#endif

////////////////////////////
// USER-ENTERED VARIABLES //
////////////////////////////
const char* filename = "KG01.txt"; // Name of file for logged data: 8.3 format (e.g, 
                             // ABCDEFGH.TXT); <= 8 chars before ".txt" is OK
const int log_minutes = 10; // Will log when the remainder of "minutes", divided by
                      // this, equals 0. For regular logging intervals, make  
                      // sure that this number divides evenly into 60.
const char* logger_name = "KG 01";


///////////////
// LIBRARIES //
///////////////

// Both for same clock, but need to create instances of both
// classes in library (due to my glomming of two libs together)
RTClib RTC;
DS3231 Clock;
// Declare current time
DateTime now;

//////////////////
// DECLARE PINS //
//////////////////

// SD card
// Digital pins:
// CLK-->13, DO-->12, DI-->11, CS-->10
// 10 is the hardware chip select; use this instead of "4" like the examples
// 13, 12, and 11 all automatically set, I guess by the new Arduino SD library
const int CSpin = 10; // KEEP AT 10; OTHERWISE, 10 CAN ONLY BE INPUT
                      // (plus, settings from further down based on this = 10)

// Analog (read) pins
// Switch to "0" and "1" for older versions of Arduino IDE
const int tempPin = A0; // Typically thermistor for temperature correction
const int sonicPin = A1; // Typically ultrasonic rangefinder (MaxBotix)
//Analog pins 4,5 attached to clock (RTC); I2C interface

// Digital pins
const int SensorPin = 4; // Activates voltage regulator to give power to sensors
const int SDpin = 8; // Turns on voltage source to SD card
const int LEDpin = 9; // LED to tell user if logger is working properly
const int wakePin = 2; // interrupt pin used for waking up via the alarm
const int interruptNum = wakePin-2; // =0 for pin 2, 1 for pin 3
const int manualWakePin = 5;

////////////////
// SD CLASSES //
////////////////

SdFat sd;
SdFile datafile;

////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////


void setup(){

////////////////////////////////////////////////////////////////
// SET VOLTAGE REFERENCE: 3.3V ON BOTTLELOGGER V0.6 AND LATER //
////////////////////////////////////////////////////////////////

// MUST do this before anything else

// We use a 3.3V regulator that we can switch on and off (to conserve power) 
// to power the instruments. Therefore, we set the analog reference to 
// "EXTERNAL". Do NOT set it to the internal 1.1V reference voltage or to 
// "DEFAULT" (VCC), UNLESS you are  absolutely sure that you need to and the
// 3.3V regulator connected to the AREF pin is off. Otherwise, you will short
// 1.1V (or VCC) against 3.3V and likely damage the MCU / fry the ADC(?)


///////////////////////////////////
// CHECK IF LOG_MINUTES IS VALID //
///////////////////////////////////

// Warn if log_minutes is bad.
// This only works for intervals of < 1 hour
if (log_minutes > 59 || log_minutes < 1){
  Serial.println(F("CANNOT LOG AT INTERVALS OF >= 1 HOUR < 1 MINUTE! LOGGER WILL FAIL!"));
  Serial.println(F("PLEASE CHANGE <log_minutes> PASSED TO FUNCTION <sleep> TO SOMETHING <=59"));
  LEDwarn(300); // 300 quick flashes of the LED - serious badness!
}

//////////////
// SET PINS //
//////////////

pinMode(wakePin,INPUT); // Interrupt to wake up
digitalWrite(wakePin,HIGH); // enable internal 20K pull-up
pinMode(manualWakePin,INPUT);
digitalWrite(manualWakePin,HIGH);
// Set the rest of the pins
// (Same function is used later to re-enable pins after they are
// set as INPUT with internal pull-ups enabled to save power
// during sleep)
pinModeRunning();
//Start out with SD, Sensor pins set LOW
digitalWrite(SDpin,LOW);
digitalWrite(SensorPin,LOW);

////////////
// SERIAL //
////////////

Serial.begin(57600);

// Announce start
announce_start();

/////////////////
// CHECK CLOCK //
/////////////////

// Check if talking to Python terminal
//char incoming = Serial.read();
//if ( incoming == 'p' ){
startup_sequence();

////////////////
// SD CARD ON //
////////////////

digitalWrite(SDpin,HIGH);
//digitalWrite(SensorPin,HIGH);

///////////////////
// WIRE: I2C RTC //
///////////////////

Wire.begin();

////////////////////////////////////////////////////////////////////
// Set alarm to go off every time seconds==00 (i.e. once a minute //
////////////////////////////////////////////////////////////////////

alarm2_1min();

///////////////////
// SD CARD SETUP //
///////////////////

// Initialize SdFat or print a detailed error message and halt
// Use half speed like the native library.
// change to SPI_FULL_SPEED for more performance.

delay(1000);

name();
Serial.print(F("Initializing SD card..."));
if (!sd.init(SPI_HALF_SPEED, CSpin)){
  Serial.println(F("Card failed, or not present"));
  LEDwarn(20); // 20 quick flashes of the LED
  sd.initErrorHalt();
}

Serial.println(F("card initialized."));
Serial.println();
LEDgood(); // LED flashes peppy happy pattern, indicating that all is well

delay(50);

name();
Serial.println(F("Logger initialization complete! Ciao bellos."));

delay(50);

digitalWrite(SDpin,LOW);

}

void loop(){

///////////////////////////////////
// Sleep; wake up with interrupt //
///////////////////////////////////

  // Go to sleep
  backtosleep:
  sleepNow();
  // Check if the logger has been awakend by someone pushing the button
  // If so, bypass everything else
  if (digitalRead(manualWakePin) == LOW){
    // Let the human know that they successfully pushed the button - yay!
    digitalWrite(LEDpin,HIGH);
    delay(200);
    digitalWrite(LEDpin,LOW);
    name();
    Serial.println(F("You pushed my button! Manual override to log."));
  }
  else{
    int minute = Clock.getMinute();
    // only go off on the 15-minute marks; "60" just to be safe
    // Could probably do minute%10 == 0 as a more elegant solution, but let's just be safe and explicit right now
    // (Tested this and it works -- OK, minute%INTERVAL will be the way of the future)
    // i.e. if (minute%15 == 0)
    // IMPORTANT NOTE: THIS PREVENTS ME FROM WAKING THE LOGGER UP ON COMMAND - I could fix this w/ use of 2 interrups,
    // but this is only really important for development / debuging
    if (minute % log_minutes == 0){
      name();
      Serial.println(F("Logging!"));
    }
    else {
      name();
      Serial.print(F("Going back to sleep for "));
      delay(2);
      Serial.print(log_minutes - (minute % log_minutes));
      delay(2);
      if (minute % log_minutes == (log_minutes -1)){
        Serial.println(F(" more minute"));
      }
      else{
        Serial.println(F(" more minutes"));
      }
      delay(2); // to finish printing before sleep cycle
      goto backtosleep;
    }
  }


  pinMode(SDpin,OUTPUT); // Seemed to have forgotten between loops...

  digitalWrite(SDpin,HIGH); // Turn on SD card before writing to it
                       // Delay required after this??
  delay(100);

  // SD init again; hope this works
  if (!sd.init(SPI_HALF_SPEED, CSpin)) sd.initErrorHalt();

  delay(100);

  // open the file for write at end like the Native SD library
  // Is there a way to not crash the whole thing if this fails?
  // Not that it seems like it will, but...
  if (!datafile.open(filename, O_WRITE | O_CREAT | O_AT_END)) {
    sd.errorHalt("SD failed");
  }

  /////////////////////////
  // Read and print time //F
  /////////////////////////

  unixDatestamp();

  //////////////////////////
  // Read analog channels //
  //////////////////////////

  // Turn voltage on via transistor
  digitalWrite(SensorPin,HIGH);
  delay(2);
  analogReference(EXTERNAL);

  thermistorB(10000,3950,25200,25,tempPin); // Cantherm
  ultrasonicMB(10,99,sonicPin,1); // 10 pings, no excitation (just turn the thing 
                                  // on/off and measure every 0.1s, which is the  
                                  // sensor refresh time)
                                  // Write data from every ping (final "1")

  delay(50);
  digitalWrite(SensorPin,LOW);
  delay(2);
  analogReference(DEFAULT);

  ////////////////////////////////////
  // MONITOR / PRINT SYSTEM VOLTAGE //
  ////////////////////////////////////

  //writeVcc();

  //////////////
  // END LINE //
  //////////////

  // No longer needed: writeVcc() handles it
  endLine();

  //////////////////////////////
  // FINAL TASKS BEFORE SLEEP //
  //////////////////////////////

  // close the file: (This does the actual sync() step too - writes buffer)
  datafile.close();

  digitalWrite(SDpin,LOW); // Turns off SD card (or it should, at least)
  alarm2reset();
  delay(10); // need time to do this?

}


////////////////////////////////////////////////////////////////////////////////
////////////////////////////////////////////////////////////////////////////////

///////////////
// FUNCTIONS //
///////////////

void clockSet(){

  byte Year;
  byte Month;
  byte Date;
  byte DoW;
  byte Hour;
  byte Minute;
  byte Second;

  bool Century=false;
  bool h12;
  bool PM;

  DateTime nowPreSet = RTC.now();  

	GetDateStuff(Year, Month, Date, DoW, Hour, Minute, Second);

	Clock.setClockMode(false);	// set to 24h
	//setClockMode(true);	// set to 12h

	Clock.setYear(Year);
	Clock.setMonth(Month);
	Clock.setDate(Date);
	Clock.setDoW(DoW);
	Clock.setHour(Hour);
	Clock.setMinute(Minute);
	Clock.setSecond(Second);

	// Give time at next five seconds
	// Should use a DateTime object for this, b/c rollover is a potential
	// problem, but this display is not mission-critical
	for (int i=0; i<5; i++){
	    delay(1000);
	    Serial.print(Clock.getYear(), DEC);
	    Serial.print(F("-"));
	    Serial.print(Clock.getMonth(Century), DEC);
	    Serial.print(F("-"));
	    Serial.print(Clock.getDate(), DEC);
	    Serial.print(F(" "));
	    Serial.print(Clock.getHour(h12, PM), DEC); //24-hr
	    Serial.print(F(":"));
	    Serial.print(Clock.getMinute(), DEC);
	    Serial.print(F(":"));
	    Serial.println(Clock.getSecond(), DEC);
	}
  delay(1000);
  unsigned long unixtime_at_receive_string = nowPreSet.unixtime();
  Serial.print(F("Logger's UNIX time at which it received the new time string: "));
  Serial.println(unixtime_at_receive_string);
  Serial.println(F("Clock set!"));
}


void GetDateStuff(byte& Year, byte& Month, byte& Day, byte& DoW, 
		byte& Hour, byte& Minute, byte& Second) {
	// Call this if you notice something coming in on 
	// the serial port. The stuff coming in should be in 
	// the order YYMMDDwHHMMSS, with an 'x' at the end.
	boolean GotString = false;
	char InChar;
	byte Temp1, Temp2;
	char InString[20];

	byte j=0;
	while (!GotString) {
		if (Serial.available()) {
			InChar = Serial.read();
			InString[j] = InChar;
			j += 1;
			if (InChar == 'x') {
				GotString = true;
			}
		}
	}
	Serial.println(InString);
	// Read Year first
	Temp1 = (byte)InString[0] -48;
	Temp2 = (byte)InString[1] -48;
	Year = Temp1*10 + Temp2;
	// now month
	Temp1 = (byte)InString[2] -48;
	Temp2 = (byte)InString[3] -48;
	Month = Temp1*10 + Temp2;
	// now date
	Temp1 = (byte)InString[4] -48;
	Temp2 = (byte)InString[5] -48;
	Day = Temp1*10 + Temp2;
	// now Day of Week
	DoW = (byte)InString[6] - 48;		
	// now Hour
	Temp1 = (byte)InString[7] -48;
	Temp2 = (byte)InString[8] -48;
	Hour = Temp1*10 + Temp2;
	// now Minute
	Temp1 = (byte)InString[9] -48;
	Temp2 = (byte)InString[10] -48;
	Minute = Temp1*10 + Temp2;
	// now Second
	Temp1 = (byte)InString[11] -48;
	Temp2 = (byte)InString[12] -48;
	Second = Temp1*10 + Temp2;
}


void pinModeRunning()
{
// Sets all pins except for the wake-up pin, which is always an input
// with a 20K pull-up
pinMode(CSpin,OUTPUT);
pinMode(SensorPin,OUTPUT);
pinMode(LEDpin,OUTPUT);
pinMode(SDpin,OUTPUT);
// Don't need to set analog pins unless using as digital; pre-set to INPUT
// Digital pins 11,12,13 set, presumably by the SD library
}

void pinModeSleep(){
  // Set all pins high and enable 20K pull-ups
  // except for interrupt pin
  for(int i=0; i<=13; i++){
    if(i!=wakePin){ // Wake pin already has these settings
      pinMode(i,INPUT); // set all pins to INPUT
      digitalWrite(i,HIGH); // Enable internal 20K pull-up
    }
  }
}


void thermistorB(float R0,float B,float Rref,float T0degC,int thermPin){
  // R0 and T0 are thermistor calibrations

  // Voltage divider
  int ADC;
  ADC = analogRead(thermPin);
  float ADCnorm = ADC/1023.0; // Normalize to 0-1
  float Rtherm = Rref/ADCnorm - Rref; // R1 = (R2-Vin)/Vout - R2

  // B-value thermistor equations
  float T0 = T0degC + 273.15;
  float Rinf = R0*exp(-B/T0);
  float T = B / log(Rtherm/Rinf);
  
  // Convert to celsius
  T = T - 273.15;
  
  ///////////////
  // SAVE DATA //
  ///////////////

  // SD

  datafile.print(T);
  datafile.print(",");
  // Echo to serial
  Serial.print(T);
  Serial.print(F(","));

}


void ultrasonicMB(int nping, int EX, int sonicPin, boolean writeAll){
  // Returns distance in cm
  // set EX=99 if you don't need it
  
  float range; // The most recent returned range
  float ranges[nping]; // Array of returned ranges
  float sumRange = 0; // The sum of the ranges measured
  float meanRange; // The average range over all the pings
  int nbadpings = 0;

//  Serial.println();
  // Get range measurements
  delay(330); // Start up - time for 2 readings w/ 30ms extra
  for(int i=0;i<nping;i++){
    if(EX != 99){
      digitalWrite(EX,HIGH);
        delay(1);
      digitalWrite(EX,LOW);
      }
    delay(150);
    range = analogRead(sonicPin);
    //error?
    if (range < 20){
      range = -9999;
      nbadpings++;
    }
    else{
      // Only add this to array if it is a valid integer
      ranges[i] = range; // 10-bit ADC value = range in cm
    }
    Serial.print(range);
    Serial.print(F(","));
    if (writeAll){
      datafile.print(range);
      datafile.print(",");
    }
  sumRange += range;
  }
 
  // Find mean of range measurements from sumRange and nping
  meanRange = sumRange/(nping-nbadpings);
  
  // Find standard deviation
  float sumsquares = 0;
  float sigma;
  for(int i=0;i<(nping-nbadpings);i++){
    // Sum the squares of the differences from the mean
    sumsquares += square(ranges[i]-meanRange);
  }
  // Calculate stdev
  sigma = sqrt(sumsquares/nping);
    
  ///////////////
  // SAVE DATA //
  ///////////////

  datafile.print(meanRange);
  datafile.print(",");
  datafile.print(sigma);
  datafile.print(",");
  // Echo to serial
  Serial.print(meanRange);
  Serial.print(F(","));
  Serial.print(sigma);
  Serial.print(F(","));

}

void unixDatestamp(){

  now = RTC.now();

  // SD

  // if the file opened okay, write to it:

  datafile.print(now.unixtime());
  datafile.print(",");
  // Echo to serial
  Serial.print(now.unixtime());
  Serial.print(F(","));
  
}

long readVcc() {
// Important to figure out battery drain
// I knew that the 1.1 reference voltage existed, but this code does a more
// low-level implementation of it (so I think b/c hard to read), and so I
// am guessing that it is also more elegant.
// From Tinker.it
// https://code.google.com/p/tinkerit/wiki/SecretVoltmeter

  long result;
  // Read 1.1V reference against AVcc
  ADMUX = _BV(REFS0) | _BV(MUX3) | _BV(MUX2) | _BV(MUX1);
  delay(2); // Wait for Vref to settle
  ADCSRA |= _BV(ADSC); // Convert
  while (bit_is_set(ADCSRA,ADSC));
  result = ADCL;
  result |= ADCH<<8;
  result = 1126400L / result; // Back-calculate AVcc in mV
  return result;
}

void writeVcc() {
  // No comma: this should always be the last thing to print

  // SD
  // Always last, so println()
  
  // First, just in case the external reference voltage is being applied,
  // turn it off
  // The way I have written the code now, this is redundant
  digitalWrite(SensorPin,LOW);
  delay(2);
  
  // Then change reference voltage source to VCC
  analogReference(DEFAULT);

  // Then write to file
  datafile.println(readVcc(),DEC); // Use a UNIX time stamp

  // Echo to serial
  Serial.println(readVcc(),DEC);
  
  // Switch back to external reference voltage
  analogReference(EXTERNAL);

}

void endLine(){
  // Ends the line in the file; do this at end of recording instance
  // before going back to sleep
  Serial.println();
  datafile.println();
  }

void sleepNow()         // here we put the arduino to sleep
{
    /* Now is the time to set the sleep mode. In the Atmega8 datasheet
     * http://www.atmel.com/dyn/resources/prod_documents/doc2486.pdf on page 35
     * there is a list of sleep modes which explains which clocks and 
     * wake up sources are available in which sleep mode.
     *
     * In the avr/sleep.h file, the call names of these sleep modes are to be found:
     *
     * The 5 different modes are:
     *     SLEEP_MODE_IDLE         -the least power savings 
     *     SLEEP_MODE_ADC
     *     SLEEP_MODE_PWR_SAVE
     *     SLEEP_MODE_STANDBY
     *     SLEEP_MODE_PWR_DOWN     -the most power savings
     *
     * For now, we want as much power savings as possible, so we 
     * choose the according 
     * sleep mode: SLEEP_MODE_PWR_DOWN
     * 
     */  
    set_sleep_mode(SLEEP_MODE_PWR_DOWN);   // sleep mode is set here

//    setPrescaler(6); // Clock prescaler of 64, slows down to conserve power
    cbi(ADCSRA,ADEN);                    // switch Analog to Digitalconverter OFF

//    pinModeSleep(); // Places all pins in INPUT with pull-ups HIGH to avoid power loss

    sleep_enable();          // enables the sleep bit in the mcucr register
                             // so sleep is possible. just a safety pin 

    /* Now it is time to enable an interrupt. We do it here so an 
     * accidentally pushed interrupt button doesn't interrupt 
     * our running program. if you want to be able to run 
     * interrupt code besides the sleep function, place it in 
     * setup() for example.
     * 
     * In the function call attachInterrupt(A, B, C)
     * A   can be either 0 or 1 for interrupts on pin 2 or 3.   
     * 
     * B   Name of a function you want to execute at interrupt for A.
     *
     * C   Trigger mode of the interrupt pin. can be:
     *             LOW        a low level triggers
     *             CHANGE     a change in level triggers
     *             RISING     a rising edge of a level triggers
     *             FALLING    a falling edge of a level triggers
     *
     * In all but the IDLE sleep modes only LOW can be used.
     */

    attachInterrupt(interruptNum,wakeUpNow, LOW); // wakeUpNow when wakePin gets LOW 

    // Copied from http://www.arduino.cc/cgi-bin/yabb2/YaBB.pl?num=1243973204
    //power_adc_disable();
    //power_spi_disable();
    //power_timer0_disable();
    //power_timer1_disable();
    //power_timer2_disable(); // uncommented because unlike forum poster, I don't rely
                            // on an internal timer
    //power_twi_disable();


    sleep_mode();            // here the device is actually put to sleep!!
                             // THE PROGRAM CONTINUES FROM HERE AFTER WAKING UP

    sleep_disable();         // first thing after waking from sleep:
                             // disable sleep...
    detachInterrupt(interruptNum);      // disables interrupt so the 
                             // wakeUpNow code will not be executed 
                             // during normal running time.

    alarm2reset();   // Turns alarm 2 off and then turns it back
                             // on so it will go off again next minute
                             // NOT BACK ON ANYMORE

//    setPrescaler(0); // Back to full strength
    sbi(ADCSRA,ADEN);                    // switch Analog to Digitalconverter ON
    //delay(3); // Slight delay before I feel OK taking readings

//    pinModeRunning(); // Set pins to their required settings to constitute a data logger

    // Copied from http://www.arduino.cc/cgi-bin/yabb2/YaBB.pl?num=1243973204
    //power_all_enable();


}

void wakeUpNow()        // here the interrupt is handled after wakeup
{
  // execute code here after wake-up before returning to the loop() function
  // timers and code using timers (serial.print and more...) will not work here.
  // we don't really need to execute any special functions here, since we
  // just want the thing to wake up
}

void alarm2reset()
{
  // Reset alarm
  Clock.turnOffAlarm(2);
  Clock.turnOnAlarm(2);
  // Not sure why, but have to use these "checking" functions, or else the clock
  // won't realize that it's been reset.
  // Here I'm just using them all; they're quick.
  // But I could probably ignore the Alarm 1 ones
  Clock.checkAlarmEnabled(1);
  Clock.checkAlarmEnabled(2);
  Clock.checkIfAlarm(1);
  Clock.checkIfAlarm(2);
}

void alarm2_1min()
{
  // Sets an alarm that will go off once a minute
  // for intermittent data logging
  // (This will use the AVR interrupt)
  Clock.turnOffAlarm(1);
  Clock.turnOffAlarm(2);
  Clock.setA2Time(1, 0, 0, 0b01110000, false, false, false); // just min mask
  Clock.turnOnAlarm(2);
}

void LEDwarn(int nflash)
{
  // Flash LED quickly to say that the SD card (and therefore the logger)
  // has not properly initialized upon restart
  for(int i=0;i<=nflash;i++)
  {
    digitalWrite(LEDpin,HIGH);
    delay(50);
    digitalWrite(LEDpin,LOW);
    delay(50);
  }
}

void LEDgood()
{
  // Peppy blinky pattern to show that the logger has successfully initialized
  digitalWrite(LEDpin,HIGH);
  delay(1000);
  digitalWrite(LEDpin,LOW);
  delay(300);
  digitalWrite(LEDpin,HIGH);
  delay(100);
  digitalWrite(LEDpin,LOW);
  delay(100);
  digitalWrite(LEDpin,HIGH);
  delay(100);
  digitalWrite(LEDpin,LOW);
}

void LEDtimeWrong(int ncycles)
{
  // Syncopated pattern to show that the clock has probably reset to January
  // 1st, 2000
  for(int i=0;i<=ncycles;i++)
  {
    digitalWrite(LEDpin,HIGH);
    delay(250);
    digitalWrite(LEDpin,LOW);
    delay(100);
    digitalWrite(LEDpin,HIGH);
    delay(100);
    digitalWrite(LEDpin,LOW);
    delay(100);
  }
}

void name(){
  // Self-identify before talking
  Serial.print(F("<"));
  Serial.print(logger_name);
  Serial.print(F(">: "));
}


void print_time(){
  boolean exit_flag = 1;
  // Wait for computer to tell logger to start sending its time
  char go;
  while( exit_flag ){
    go = Serial.read();
    if( (go == 'g') && exit_flag ){
      exit_flag = 0; // Exit loop once this is done
      // Print times before setting clock
      for (int i=0; i<5; i++){
        now = RTC.now();
        Serial.println(now.unixtime());
        if ( i<4 ){
          // No need to delay on the last time through
          delay(1000);
        }
      }
    }
  } // This is the end of the while loop for clock setting and passing the old
    // time over to the computer.
}

void set_time_main(){
  // Now set clock and returns 5 more times as part of that function
  // First thing coming in should be the time from the computer
  boolean exit_flag = 1;
  while( exit_flag ){
    if ( Serial.available() ){
      clockSet();
      exit_flag = 0; // Totally out of loop now
    }
  }
}
void announce_start(){
  Serial.println();
  name();
  Serial.println(F(" = this logger's name."));
  Serial.println();
  delay(500);
  Serial.println(F("********************** Logger initializing. **********************"));
}

void startup_sequence(){
  boolean comp = 0;
  unsigned long unixtime_at_start;
  int millisthen = millis();
  while ( (millis() - millisthen) < 2000 && (comp == 0)){
    if ( Serial.available() ){
      comp = 1;
    }
  }
  name();
  Serial.println(F("HELLO, COMPUTER."));
  delay(500);
  if ( comp ){
    delay(4000); // Give Python time to print
    name();
    Serial.print(F("LOGGING TO FILE ["));
    Serial.print(filename);
    Serial.println(F("]"));
    delay(1500);
    name();
    Serial.print(F("UNIX TIME STAMP ON MY WATCH IS: "));
    now = RTC.now();
    unixtime_at_start = now.unixtime();
    Serial.println(unixtime_at_start);
    delay(1500);
    if(unixtime_at_start < 1000000000){
      name();
      Serial.println(F("Uh-oh: that doesn't sound right! Clock reset to 1/1/2000?"));
      LEDtimeWrong(3);
      print_time();
      set_time_main();
      delay(2000);
      name();
      Serial.println(F("Thanks, computer! I think I'm all set now."));
    }
    else{
      name();
      //Serial.println(F("Clock is probably fine"));
      ///*
      Serial.println(F("How does that compare to you, computer?"));
      delay(1500);
      print_time();
      delay(1500);
      name();
      Serial.println(F("Would you like to set the logger's clock to the computer's time? (y/n)"));
      boolean waiting = 1;
      char yn;
      while ( waiting ){
        if ( Serial.available() ){
          yn = Serial.read();
          if ( yn == 'y' || yn == 'Y'){
            waiting = 0;
            set_time_main();
          }
          else if ( yn == 'n' || yn == 'N'){
            waiting = 0;
            name();
            Serial.println(F("Not selecting time; continuing."));
            delay(1500);
          }
          else{
            name();
            Serial.println(F("Please select <y> or <n>."));
          }
        }
      }//*/
    }
  }
  else{
    // No serial; just blink
    now = RTC.now();
    unixtime_at_start = now.unixtime();
    // Keep Serial just in case computer is connected w/out Python terminal
    Serial.print(F("Current UNIX time stamp according to logger is: "));
    Serial.println(unixtime_at_start);
    if(unixtime_at_start < 1000000000){
      LEDtimeWrong(3);
    }
  }
  if ( comp ){
    delay(1500);
    name();
    Serial.println(F("Now beginning to log."));
    delay(1000);
  }
}

