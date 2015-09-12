#!/usr/bin/python
#Doug Fultz
#COMP512 - Advanced Operating Systems
#Project - 52 Pick Up
#-Libraries------------------------------------------------
import sys
import time
# Requires the python-tk package
import Tkinter
import socket
import threading
import os
#-Globals--------------------------------------------------
HOST=''
PORT=6155
PLAYER=None
TITLE=''
hostSocket=None
clientSocket=None
clientAddress=None
#cards=52
cardColumns=13
cardBackH=None
cardBackC=None
cardFace=[]
cardMap=["01c","02c","03c","04c","05c","06c","07c","08c","09c","10c","11c","12c","13c","01d","02d","03d","04d","05d","06d","07d","08d","09d","10d","11d","12d","13d","01s","02s","03s","04s","05s","06s","07s","08s","09s","10s","11s","12s","13s","01h","02h","03h","04h","05h","06h","07h","08h","09h","10h","11h","12h","13h"]
cards=[]
logClock=1
logClockSem=threading.Semaphore()
recvThread=None
cardThread=None
testThread=None
screenSem=threading.Semaphore()
#-Card-class-----------------------------------------------
class cardClass:
    def __init__(self,iPlayer,iTS):
        self.player=iPlayer
        self.timeStamp=iTS
#-event-Class----------------------------------------------
class eventType:
    def __init__(self,iCard,iTS,iPlayer):
        self.card=iCard
        self.timeStamp=iTS
        self.player=iPlayer
#-GUI-Class------------------------------------------------
class fiftytwopickup(Tkinter.Tk):
    def __init__(self,parent):
        Tkinter.Tk.__init__(self,parent)
        self.parent=parent
        self.initialize()
    
    def initialize(self):
        #Choose Grid Layout
        self.grid()
        
        #Add message label
        self.msg=Tkinter.StringVar()
        messageLabel=Tkinter.Label(self,textvariable=self.msg)
        messageLabel.grid(column=0,row=0,columnspan=6)
        self.msg.set("Click on the cards below, the player with the most cards wins")
        
        #Add a label in the upper right corner to show score and declare winners
        self.score=Tkinter.StringVar()
        scoreLabel=Tkinter.Label(self,textvariable=self.score)
        scoreLabel.grid(column=7,row=0,columnspan=4)
        self.score.set("Host: 0 Client: 0")
        
        self.cardButton=[]
        self.running=threading.Event()
        curRow=1
        global cardBackH
        global cardBackC
        global cardFace
        global cards
        cardBackH=Tkinter.PhotoImage(file="./cardset-standard/back191.gif")
        cardBackC=Tkinter.PhotoImage(file="./cardset-standard/back192.gif")
        
        for i in range(len(cardMap)):
            cardFace.append(Tkinter.PhotoImage(file="./cardset-standard/"+str(cardMap[i])+".gif"))
            cards.append(cardClass(0,0))
        i=0
        while (i<len(cardMap)):
            for j in range(cardColumns):
                if (i>=len(cardMap)):
                    break
                
                #Using lambda as a wrapper to pass a parameter to the command function
                #https://stackoverflow.com/questions/6920302/passing-argument-in-python-tkinter-button-command
                #Making a closure on lambda so that it functions as expected
                #https://stackoverflow.com/questions/16224368/tkinter-button-commands-with-lambda-in-python
                self.cardButton.append(Tkinter.Button(self,image=cardFace[i],command=lambda i=i: self.cardClicked(i)))
                self.cardButton[i].grid(column=j,row=curRow)
                i=i+1
            curRow=curRow+1
        self.resizable(False,False)
        self.update()
        
        #On Window Close
        #https://stackoverflow.com/questions/3295270/python-tkinter-x-button-control-the-button-that-close-the-window
        self.protocol('WM_DELETE_WINDOW', self.OnClose)
        
        #start read socket thread
        global recvThread
        recvThread=threading.Thread(name="recvThread",target=self.recv)
        #recvThread.daemon=True
        recvThread.start()
        
        #start card back thread
        global cardThread
        cardThread=threading.Thread(name="cardThread",target=self.cardUpdate)
        #cardThread.daemon=True
        cardThread.start()
        
    def OnClose(self):
        echo("Window Closed")
        self.running.set()
        #self.destroy()
        self.withdraw()
        echo("Waiting for threads to stop")
        i=0
        time.sleep(1)
        while (threading.activeCount()>1):
            echo("Active threads: "+str(threading.enumerate()))
            i=i+1
            if(i>5):
                break
            time.sleep(1)
        time.sleep(1)
        self.quit()
    
    def cardClicked(self,id):
        global cards
        #TODO
        #Increase verbosity and include logical timestamps
        echo("Card Clicked "+cardMap[id])
        #disable button
        self.cardButton[id].configure(state=Tkinter.DISABLED)
        #create event
        evnt=eventType(id,getTS(),PLAYER)
        #check if card already been grabbed
        if (cards[evnt.card].player>0):
            #compare timestamps
            if (cards[evnt.card].timeStamp==evnt.timeStamp):
                #timestamps concurrent, host gets card
                cards[evnt.card].player=1
            elif (cards[evnt.card].timeStamp<evnt.timeStamp):
                #card already picked up and accounted for, nothing to do
                pass
            elif (cards[evnt.card].timeStamp>evnt.timeStamp):
                #update card
                cards[evnt.card].player=evnt.player
                cards[evnt.card].timeStamp=evnt.timeStamp
        else:
            #card not already picked up, update card
            cards[evnt.card].player=evnt.player
            cards[evnt.card].timeStamp=evnt.timeStamp
            #send event to socket
            echo("Sending card: "+cardMap[evnt.card]+" TS: "+str(evnt.timeStamp))
            clientSocket.send(eventToStr(evnt))
        self.update()
        
    def recv(self):
        global cards
        echo("recv: started")
        while not self.running.isSet():
            try:
                msg=clientSocket.recv(1024)
                evnts=strToEvent(msg)
                for evnt in evnts:
                    #TODO
                    #Increase verbosity and print logical timestamp
                    print("Card Taken   "+cardMap[evnt.card])
                    #disable button for card
                    self.cardButton[evnt.card].configure(state=Tkinter.DISABLED)
                    #get new timeStamp
                    ts=getTS(evnt.timeStamp)
                    echo("Received card: "+cardMap[evnt.card]+" TS: "+str(evnt.timeStamp)+" at TS: "+str(ts))
                    #check if card already been grabbed
                    if (cards[evnt.card].player>0):
                        #compare timestamps
                        if (cards[evnt.card].timeStamp==evnt.timeStamp):
                            #timestamps concurrent, host gets card
                            cards[evnt.card].player=1
                        elif (cards[evnt.card].timeStamp<evnt.timeStamp):
                            #this player picked up card first, nothing to do
                            pass
                        elif (cards[evnt.card].timeStamp>evnt.timeStamp):
                            #other player picked up card first, update our deck
                            cards[evnt.card].player=evnt.player
                            cards[evnt.card].timeStamp=evnt.timeStamp
                    else:
                        #update card
                        cards[evnt.card].player=evnt.player
                        cards[evnt.card].timeStamp=evnt.timeStamp
            except:
                pass
        echo("recv: stopped")
        
    def cardUpdate(self):
        echo("cardUpdate: started")
        while not self.running.isSet():
            hostScore=0
            clientScore=0
            unclaimed=0
            for i in range(len(cardMap)):
                #echo("cardUpdate: i: "+str(i))
                if self.running.isSet():
                    break
                try:
                    if (cards[i].player==1):
                    #if (cards[i].player==1):
                        #echo("cardUpdate: player 1")
                        hostScore=hostScore+1
                        self.cardButton[i].configure(image=cardBackH)
                    elif (cards[i].player==2):
                    #elif (cards[i].player==2):
                        #echo("cardUpdate: player 2")
                        clientScore=clientScore+1
                        self.cardButton[i].configure(image=cardBackC)
                    else:
                        #count unclaimed cards
                        unclaimed=unclaimed+1
                except:
                    echo("cardUpdate: Tried setting card "+str(i)+", but it's gone")
                #echo("host: "+str(hostScore))
                #echo("clnt: "+str(clientScore))
                #echo("uncd: "+str(unclaimed))
            self.score.set("Host: "+str(hostScore)+" Client: "+str(clientScore)+" free: "+str(unclaimed))
            if(unclaimed==0):
                if(hostScore>clientScore):
                    winmsg="Host WINS!"
                elif(clientScore>hostScore):
                    winmsg="Client WINS!"
                else:
                    winmsg="TIE!"
                self.score.set(str(winmsg)+" "+str(self.score.get()))
                self.update()
                self.running.set()
        echo("cardUpdate: stopped")
#----------------------------------------------------------
def eventToStr(evnt):
    return(str(evnt.card)+","+str(evnt.timeStamp)+","+str(evnt.player)+";")
#----------------------------------------------------------
def echo(string):
    #get screen sem
    if (screenSem.acquire()):
        #print to screen
        print(string)
        #release screen sem
        screenSem.release()
#----------------------------------------------------------
def strToEvent(strng):
    evnts=[]

    for evnt in strng.split(";"):
        temp=evnt.split(",")
        try:
            id=unicode(temp[0])
            ts=unicode(temp[1])
            pl=unicode(temp[2])
        except:
            pass
        
        if (id.isnumeric() and ts.isnumeric() and pl.isnumeric()):
            evnts.append(eventType(int(id),int(ts),int(pl)))
    return(evnts)
#----------------------------------------------------------
def getTS(cur=None):
    global logClock
    global logClockSem
    
    if (cur==None):
        with logClockSem:
            logClock=logClock+1
            temp=logClock
        return(temp)
    if (isinstance(cur,int)):
        with logClockSem:
            temp=logClock
        if (cur<=temp):
            return(getTS(None))
        
        if (cur>temp):
            with logClockSem:
                logClock=cur
            return(getTS(None))
    else:
        raise TypeError
#=MAIN=====================================================
if __name__ == "__main__":
    #print(sys.argv)
    if (not len(sys.argv)==2):
        echo("Possible options:")
        echo("host     : Host a new game")
        echo("hostname : hostname of game to join")
        sys.exit(1)
    
    #Host a new game
    if (sys.argv[1]=="host"):
        echo("Hosting a new game.")
        PLAYER=1
        TITLE="52 Pickup Host"
        #create host socket
        hostSocket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        #https://stackoverflow.com/questions/6380057/python-binding-socket-address-already-in-use
        hostSocket.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        #hostSocket.settimeout(1)
        echo("Binding socket on port "+str(PORT))
        hostSocket.bind((HOST,PORT))
        hostSocket.listen(1)
        
        echo("Waiting for other player.")
        (clientSocket,clientAddress)=hostSocket.accept()
        clientSocket.setblocking(0)
        hostSocket.setblocking(0)
        echo("Accepted connection from "+str(clientAddress))
        
        echo("Closing listening socket.")
        #hostSocket.shutdown(socket.SHUT_RD)
        #hostSocket.shutdown(1)
        hostSocket.close()
    
    #Join an existing game
    else:
        HOST=sys.argv[1]
        echo("Joining an existing game at "+HOST)
        PLAYER=2
        TITLE="52 Pickup Client"
        #create client socket
        clientSocket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        echo("Connecting to "+HOST+" on port "+str(PORT))
        echo("Resolving "+HOST+" to "+socket.gethostbyname(HOST))
        clientSocket.connect((socket.gethostbyname(HOST),PORT))
        clientSocket.setblocking(0)
        echo("Connected to "+str(clientSocket.getpeername()))

    echo(str(threading.enumerate()))
    
    #Start game
    app=fiftytwopickup(None)
    app.title(TITLE)
    app.mainloop()
    
    echo("Closing client socket")
    #clientSocket.shutdown(socket.SHUT_RD)
    clientSocket.close()
    echo(threading.activeCount())
    while (threading.activeCount()>1):
        echo(str(threading.enumerate()))
        echo("---------------------------------")
        echo("Looks like a thread isn't playing nice, committing suicide.")
        os.system("pkill pickup")
        time.sleep(1)
    sys.exit(0)