#include <SPI.h>
#include <Ethernet.h>
#include "Keyboard.h"

#define bootDelay 9000 //time to get the boot menu from wol, in ms
#define keyPressDelay 100 //in ms
#define resetDelay 4

byte mac[] = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

int wolPort = 9;
byte remote_MAC_ADD[] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
byte broadCastIp[] = { 255, 255, 255, 255 };

IPAddress ip(192, 168, 1, 5);
EthernetServer server(80);

void setup() 
{
  Keyboard.begin();

  Ethernet.begin(mac, ip);

  if (Ethernet.hardwareStatus() == EthernetNoHardware || Ethernet.linkStatus() == LinkOFF) 
  {
    return;
  }
  server.begin();
}


void loop() 
{
  EthernetClient client = server.available();
  if (client) 
  {
    // an http request ends with a blank line
    String message = "";
    boolean currentLineIsBlank = true;
    while (client.connected()) {
      if (client.available()) 
      {
        char c = client.read();
        // if you've gotten to the end of the line (received a newline
        // character) and the line is blank, the http request has ended,
        // so you can send a reply
        if (c == '\n' && currentLineIsBlank) 
        {
          String param = message.substring(5, message.indexOf("HTTP")-1);
          // send a standard http response header
          client.println("HTTP/1.1 200 OK");
          client.println("Access-Control-Allow-Origin: *");
          if(param == "")
          {
            client.println("Content-Type: text/html");
            client.println("Connection: close");
            client.println();
            client.print(F(\
              "<html>\
                <head>\
                    <title>Wake On Lan</title>\
                    <meta name='viewport' content='width=device-width, initial-scale=1'>\
                    <style>html{background-color:#222222;}.pure-button{display:inline-block;line-height:normal;white-space:nowrap;vertical-align:middle;text-align:center;cursor:pointer;-webkit-user-drag:none;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;-webkit-box-sizing:border-box;box-sizing:border-box}.pure-button::-moz-focus-inner{padding:0;border:0}.pure-button-group{letter-spacing:-.31em;text-rendering:optimizespeed}.opera-only :-o-prefocus,.pure-button-group{word-spacing:-.43em}.pure-button-group .pure-button{letter-spacing:normal;word-spacing:normal;vertical-align:top;text-rendering:auto}.pure-button{font-family:inherit;font-size:100%;padding:.5em 1em;color:rgba(0,0,0,.8);border:none transparent;background-color:#e6e6e6;text-decoration:none;border-radius:2px}.pure-button-hover,.pure-button:focus,.pure-button:hover{background-image:-webkit-gradient(linear,left top,left bottom,from(transparent),color-stop(40%,rgba(0,0,0,.05)),to(rgba(0,0,0,.1)));background-image:linear-gradient(transparent,rgba(0,0,0,.05) 40%,rgba(0,0,0,.1))}.pure-button:focus{outline:0}.pure-button-active,.pure-button:active{-webkit-box-shadow:0 0 0 1px rgba(0,0,0,.15) inset,0 0 6px rgba(0,0,0,.2) inset;box-shadow:0 0 0 1px rgba(0,0,0,.15) inset,0 0 6px rgba(0,0,0,.2) inset;border-color:#000}.pure-button-disabled,.pure-button-disabled:active,.pure-button-disabled:focus,.pure-button-disabled:hover,.pure-button[disabled]{border:none;background-image:none;opacity:.4;cursor:not-allowed;-webkit-box-shadow:none;box-shadow:none;pointer-events:none}.pure-button-hidden{display:none}.pure-button-primary,.pure-button-selected,a.pure-button-primary,a.pure-button-selected{background-color:#0078e7;color:#fff}.pure-button-group .pure-button{margin:0;border-radius:0;border-right:1px solid rgba(0,0,0,.2)}.pure-button-group .pure-button:first-child{border-top-left-radius:2px;border-bottom-left-radius:2px}.pure-button-group .pure-button:last-child{border-top-right-radius:2px;border-bottom-right-radius:2px;border-right:none}.button-error,.button-secondary,.button-success,.button-warning{color:#fff;border-radius:4px;text-shadow:0 1px 1px rgba(0,0,0,.2)}.button-success{background:#1cb841}.button-error{background:#ca3c3c}.button-warning{background:#df7514}</style>\
                </head>\
                <body>\
                  <br><a class='button-success pure-button' onclick='redir(\"/0/on\")'>Start Windows</a>&nbsp;&nbsp;\
                  <a class='button-error pure-button' onclick='redir(\"/0/off\")'>Stop Windows</a><br><br>\
                  <a class='button-success pure-button' onclick='redir(\"/1/on\")'>Start Linux</a>&nbsp;&nbsp;\
                  <a class='button-error pure-button' onclick='redir(\"/1/off\")'>Stop Linux</a><br><br>\
                  <a class='button-warning pure-button' onclick='redir(\"/lock\")'>Lock</a>\
                </body>\
                <script>function redir(path) { window.location.href = window.location.href + path }</script>\
              </html>")
            );
          }
          else
          {
            client.println("Content-Type: application/json");
            client.println("Connection: close");
            client.println();
            client.print("{\"command\":\"");
            client.print(param);
            client.print("\",\"response\":\"");
            client.print(doAction(param));
            client.println("\"}");
          }
          break;
        }
        if (c == '\n') {
          // you're starting a new line
          currentLineIsBlank = true;
          
        } else if (c != '\r') {
          // you've gotten a character on the current line
          currentLineIsBlank = false;
        }
        message += c;
      }
    }
    delay(1);
    client.stop();
  }

}

//========================================================= WOL functions =========================

void sendWol()
{
    byte magicPacket[102];
    int i,c1,j=0;
   
    for(i = 0; i < 6; i++,j++){
        magicPacket[j] = 0xFF;
    }
    for(i = 0; i < 16; i++){
        for( c1 = 0; c1 < 6; c1++,j++)
          magicPacket[j] = remote_MAC_ADD[c1];
    }
    
    EthernetUDP Udp;
    Udp.begin(wolPort);
    Udp.beginPacket(broadCastIp, wolPort);
    Udp.write(magicPacket, sizeof magicPacket);
    Udp.endPacket();
}

//========================================================= Actions =============================================

String doAction(String param)
{
  //0 = Windows, 1 = Ubuntu
  
  if (param == "0/on")
  {
    sendWol();
    delay(bootDelay);
    Keyboard.println(); //enter
  }
  else if(param == "0/off")
  {
    Keyboard.press(KEY_LEFT_GUI);
    Keyboard.press('d');
    delay(keyPressDelay);
    Keyboard.releaseAll(); // Windows + D
    
    delay(keyPressDelay);
    
    Keyboard.press(KEY_LEFT_ALT);
    Keyboard.press(KEY_F4);
    delay(keyPressDelay);
    Keyboard.releaseAll(); // Alt + F4
    
    delay(keyPressDelay);
    
    Keyboard.println(); //enter

    delay(1000);
    // if the sequence failed (the computer is likely locked), continue with a sequence to poweroff from the lockscreen
    // enter -> 4 tab -> enter -> down -> enter -> enter
    
    for(char i = 0; i<4; i++) {
      Keyboard.press(KEY_TAB); //tab
      delay(keyPressDelay);
      Keyboard.releaseAll();
    }
    Keyboard.println(); //enter
    delay(keyPressDelay);
    
    Keyboard.press(KEY_DOWN_ARROW); //down
    delay(keyPressDelay);
    Keyboard.releaseAll();
    
    Keyboard.println(); //enter
    delay(keyPressDelay);
    Keyboard.println(); //enter
    delay(keyPressDelay);  
  }
  else if(param == "1/on")
  {
    sendWol();
    delay(bootDelay);
    Keyboard.press(KEY_DOWN_ARROW);
    delay(keyPressDelay);
    Keyboard.releaseAll();
    
    delay(keyPressDelay);
    
    Keyboard.println(); //enter
  }
  else if(param == "1/off")
  {
    Keyboard.press(KEY_LEFT_CTRL);
    Keyboard.press(KEY_LEFT_ALT);
    Keyboard.press('s');
    delay(keyPressDelay);
    Keyboard.releaseAll(); // Ctrl + Alt + S
  }
  else if(param == "lock")
  {
    Keyboard.press(KEY_LEFT_GUI);
    Keyboard.press('l');
    delay(keyPressDelay);
    Keyboard.releaseAll(); // Win + L
  }
  else if(param == "status")
  {
    Serial.begin(9600);
    if (Serial)
      return "true";
    else
      return "false";
    Serial.end();
  }
  else
  {
    return "error";
  }
  
  return "ok";
}