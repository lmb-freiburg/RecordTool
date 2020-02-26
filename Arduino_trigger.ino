#include <TimerOne.h>
#include <SoftwareSerial.h>
// check signal parameters from serial
// if first charakter 'S' start interrupt
// integer following S ist the FPS-setting
// if first charakter 'Q' stop interrupt
// dutycycle is set in dependancy of freq  to be ~ 5ms 
// if first charakter 'T' send following string to intan
const byte rxPin = 2;
const byte txPin = 3;
SoftwareSerial mySerial(rxPin, txPin,1);
const int LedPin = 9;
bool pinStatus = 0;
long fps = 30;
float duration = 5000.0;
int input;
float dutyCycle = 30.0;
void setup(void)
{
  Serial.begin(9600);
  mySerial.begin(600);
  digitalWrite(LedPin,0);
}

void loop(void)
{
  if(Serial.available()>0)
  {
    input=Serial.read();
    if (input=='P') // Poll the arduino, expect answer bit '1' 
    {
      Serial.print(1);
    }

    if (input=='Q')
    {
      if (pinStatus==1)
      {
        Timer1.disablePwm(LedPin);
        Timer1.stop();
        Serial.println(3);
        pinStatus=0;
      }
    }

    if (input=='S')
    {
      fps=Serial.parseInt(); 
      Serial.println(2);
      Serial.print(fps);     
      //duration=(float)Serial.parseInt(); // if we also want to set a duration of pulse
      if (pinStatus==0)
      {
        Timer1.initialize(1000000/fps);  // 40 us = 25 kHz
        dutyCycle = duration/(1000000/fps); // calculate duty cycle to have pulse length ~5ms
        Timer1.pwm(LedPin, (dutyCycle) * 1023);
        pinStatus=1;
      }
    }
    if (input=='T')
    {
      String text=Serial.readString();
      mySerial.print(text); //Write the text from Serial port
    }
    delay(100);
  } 
}
