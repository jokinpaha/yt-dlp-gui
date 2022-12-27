# !/usr/bin/python3
from tkinter import *
import subprocess
from tkinter import messagebox
import tkinter.ttk
import os


top = Tk()
top.geometry("500x125")

update = subprocess.run(['yt-dlp', '-U'], stdout=subprocess.PIPE)
uppia = update.stdout.decode('utf-8')

def download(url):
    print('Starting download')    
    p1 = subprocess.run(['yt-dlp','--ffmpeg-location',os.path.join('','ffmpeg', 'bin'),'-P',os.path.join('','DOWNLOADS'), url])
    #output = p1.communicate()[0]
    #print(output)
	
def update():
    print('Updating')    
    p2 = subprocess.run(['python', '-m', 'pip', 'install', '-U', 'yt-dlp'])
    #output = p1.communicate()[0]
    #print(output)

def popup(event):
    try:
        menu.tk_popup(event.x_root,event.y_root) # Pop the menu up in the given coordinates
    finally:
        menu.grab_release() # Release it once an option is selected

def paste():
    clipboard = top.clipboard_get() # Get the copied item from system clipboard
    url.insert('end',clipboard) # Insert the item into the entry widget

def copy():
    inp = url.get() # Get the text inside entry widget
    top.clipboard_clear() # Clear the tkinter clipboard
    top.clipboard_append(inp) # Append to system clipboard

menu = Menu(top,tearoff=0) # Create a menu
menu.add_command(label='Copy',command=copy) # Create labels and commands
menu.add_command(label='Paste',command=paste)


L1 = Label(top, text = "Video url:")
L1.grid(column = 1, row = 2, padx = 10)

url = Entry(top, bd =5)
url.grid(column = 2, row = 2, ipadx = 100)

url.bind('<Button-3>',popup) # Bind a func to right click

DLbutton = Button(top, text = "Download", command = lambda:download(url.get()))
DLbutton.grid(column = 5, row = 2, padx = 10, pady = 10)

tkinter.ttk.Separator(top, orient=HORIZONTAL).grid(column=0, row=5, columnspan=20, pady = 10, sticky='ew')

L2 = Label (top, text = uppia)
L2.grid (column = 2, row = 15)

UPDbutton = Button(top, text = "Update", command = lambda:update())
UPDbutton.grid(column = 5, row = 15)

#url = "https://youtu.be/-CXgH2HrdQA"

top.mainloop()