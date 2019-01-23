from subprocess import call
import pyqrcode
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import pandas as pd
import time

'''
2.625" x 1" label is 527x200 px
4"x6" label should be 812 x 1218 px
8.5x11 is 2550x3300px at 300 DPI

barcodes were 166x166 on the skinny labels, under 1"x1".
Let's try 270x270, which will really be 230x230 with 20px on each side (need to cut in half).
Three labels across, four labels down. Should write link under each label.

Outcome of this one: Needs more space around the label edges. Needs more whitespace between labels. Possibly can only do 2x3, even at that size? No, it just needs more whitespace...
'''

#usage: python barcodize_30up.py urllist_txt outpdfname short_or_long Y_for_sorted_by_caption

def main():
	os.makedirs("out", exist_ok = True)
	time_start = time.time()
	mylabelfile = sys.argv[1]
	outfilename = "out_30up.pdf"
	if len(sys.argv) >= 3:
		outfilename = sys.argv[2]
	linktype = "short"
	if len(sys.argv) >= 4:
		linktype = sys.argv[3]
	sort = False
	if len(sys.argv) >= 5:
		if sys.argv[4] not in ["false", "False", "N", "no"]:
			sort = True
	labeldata = readURLCaptions(mylabelfile, linktype, sort)
	barcodes = makeAllBarcodes(labeldata)
	lefttoprint = len(barcodes)
	pagenum = 1
	while lefttoprint > 0:
		thischunk = barcodes[30*(pagenum-1):30*pagenum]
		thisfilename = "out/30up_"+str(pagenum).zfill(5)+".png"
		pageim = placeLabels_onPage(thischunk)
		cv2.imwrite(thisfilename, pageim)
		call("convert -units PixelsPerInch -density 300 \""+thisfilename+"\" \""+thisfilename+"\"", shell = True)
		lefttoprint -= 30
		pagenum += 1
	call("convert out/*.png \""+outfilename+"\"", shell=True)
	call("rm out/*.png", shell=True)
	time_end = time.time()
	print(round(time_end - time_start, 2), "seconds to make", len(barcodes), "barcodes.")
	return

def readURLCaptions(mylabelfile, linktype = "short", sort=False):
	mydata = pd.read_csv(mylabelfile, sep="\t", dtype=str).replace(np.nan, '', regex=True).replace("^nan$", '', regex=True)
	if sort == True:
		mydata = mydata.sort_values('Caption')
		#have to reindex locs too
		mydata = mydata.reset_index(drop = True)
	##all urls sorted, no caption URLs excluded
	if linktype == "short":
		labeldata = [{"url": mydata.loc[i]["Short URL"], "caption":mydata.loc[i]["Caption"].replace("\\n", "\n")} for i in range(len(mydata))]
		labeldata = list(filter(lambda x: len(x["url"]) > 3, labeldata))
		labeldata = list(filter(lambda x: len(x["caption"]) > 0, labeldata))
	elif linktype == "long":
		labeldata = [{"url": mydata.loc[i]["URL"], "caption":mydata.loc[i]["Caption"].replace("\\n", "\n")} for i in range(len(mydata))]
		labeldata = list(filter(lambda x: len(x["url"]) > 3, labeldata))
		labeldata = list(filter(lambda x: len(x["caption"]) > 0, labeldata))
	return labeldata

#
#300 DPI sheets, 3300 px x 2550 px
def placeLabels_onPage(labellist):
	labelwidth = 775
	labelheight = 300
	#firstoffset_x = 30
	firstoffset_x = 55
	firstoffset_y = 160
	step_y = 300
	step_x = 833
	pageim = np.ones((3300, 2550, 3), np.uint8)*255
	#30 positions. starts in top left, going down up to 10 rows, then right up to 3 columns. 10 rows 3 columns.
	pagepos = 0 #ends at 29
	while pagepos < 30 and pagepos < len(labellist):
		x_pos = pagepos // 10
		y_pos = pagepos % 10
		thislabel_im = labellist[10*x_pos+y_pos]
		x_start = firstoffset_x + x_pos * step_x
		x_end = firstoffset_x + x_pos * step_x + labelwidth
		y_start = firstoffset_y + y_pos * step_y
		y_end = firstoffset_y + y_pos * step_y + labelheight
		pageim[y_start:y_end, x_start:x_end] = thislabel_im
		pagepos += 1
	return pageim

def makeAllBarcodes(datalist):
	labellist = []
	for i in range(len(datalist)):
		thisimg = makeBarcode(datalist[i]["url"], datalist[i]["caption"])
		labellist.append(thisimg)
	call("rm \"thisurl.png\"", shell=True)
	return labellist

def makeBarcode(myurl, mycaption = ""):
	qr = pyqrcode.create(myurl)
	#qr.svg("thisurl.svg", scale=4)
	#call("convert thisurl.svg thisurl.png", shell = True)
		#not working because of no rsvg-convert delegate. weird.
	qr.png("thisurl.png", scale=9)
		#needs pypng
	page_width = 775
	page_height = 300
	qr_size = 300
	baseimg = np.ones((page_height, page_width, 3), np.uint8)*255
	qrimg = cv2.imread("thisurl.png")
	qrimg = cv2.resize(qrimg, dsize = (qr_size, qr_size), interpolation = cv2.INTER_LINEAR)
	qrimg = np.rot90(qrimg) #scans best when the three corner boxes look like an "L"
	qrimg = np.rot90(qrimg)
	baseimg[0:qr_size, 0:qr_size] = qrimg
	qrimg = np.rot90(qrimg) #should rotate again so the L is in same place when ripped.
	qrimg = np.rot90(qrimg)
	baseimg[0:qr_size, -qr_size:] = qrimg
	#
	baseimg = cv2.cvtColor(baseimg, cv2.COLOR_BGR2RGB)
	pilimg = Image.fromarray(baseimg)
	drawthis = ImageDraw.Draw(pilimg)
	mycaption = mycaption.replace("\\n", "\n")
	drawthis.text((303, 60), mycaption, font = ImageFont.truetype('/usr/share/fonts/truetype/msttcorefonts/arial.ttf', 30), fill = (0, 0, 0))
	baseimg = np.asarray(pilimg)
	baseimg = cv2.cvtColor(baseimg, cv2.COLOR_RGB2BGR)
	#call("rm \"thisurl.png\"", shell=True)
	return baseimg


if __name__ == "__main__":
	main()
#
#


#######
##utils
def showImage(myimage, mypath = "zzztestcoords.jpg", show = True):
	if mypath == None:
		mypath = "zzztestcoords.jpg"
	cv2.imwrite(mypath, myimage)
	if show:
		call("wine \"c:/Program Files/IrfanView/i_view64.exe\" + \"" +mypath+"\"", shell=True)
	return

def sshow(image, name = None, showit = True):
	if type(name) == type(None):
		showImage(recon(image), mypath = None, show = showit)
	else:
		showImage(recon(image), name, showit)
	return

def recon(myimage_float): #reconstitutes float images to uint8
	dst = np.empty(myimage_float.shape)
	#return np.round(cv2.normalize(myimage_float, dst = dst, alpha = 0, beta = 255, norm_type = cv2.NORM_MINMAX)).astype(np.uint8)
		#slow?
	return cv2.normalize(myimage_float, dst = dst, alpha = 0, beta = 255, norm_type = cv2.NORM_MINMAX).astype(np.uint8)
