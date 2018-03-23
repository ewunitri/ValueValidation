# -*- coding: utf-8 -*-
"""
Created on Fri Mar 16 16:56:31 2018

@author: 455495
"""

import re
from os import listdir, getcwd
from os.path  import join, isfile



#-------------------------------------------------------------------------------   
#   parse_Tag2Value()
#   parse the 'linesAmt' of datalines starting from linStIdx and return to float value
#-------------------------------------------------------------------------------   
def parse_Tag2Value(datalines,lineStIdx,linesAmt):
    
    ## build a list to store all datalines from lineStIdx
    lines = []
    for i in range(linesAmt):
        lines.append(datalines[lineStIdx+i])
    
    str_value=''
    for line in lines:
        ## search the x value within value="x", omit the others, 
        ## join the values into a string
        tmp = re.search(r'Char(.+)value=\"(.+)\" (.+)',line)
        if tmp:
            str_value += tmp.group(2)
        else:
            return -1.0     ## return negative value if value pattern not found
        
    ## the string must begin with '$', otherwise return negative value
    if (str_value[0] != '$'):
        return -1.0
    
    ## obtain only the decimal char or decimal point
    rtn = re.sub(r"[^\d\.]",'',str_value)
    
    return float(rtn)





#-------------------------------------------------------------------------------   
#   parse_pairTag()
#   search the given tagStr within lineLtd begin from lineStIdx of datalines,
#   return the beginning of the tagStr and how far of the tagStr ends at
#-------------------------------------------------------------------------------   
def parse_pairTag(datalines,lineStIdx,lineLtd,tagStr):
  
    taglineRange = 0 
    taglineSt = lineStIdx
    ## set beginning and ending pattern
    patBegin = r'<{}'.format(tagStr)    
    patEnd = r'</{}>'.format(tagStr)
    #print 'patBegin: {}'.format(patBegin)
    #print 'patEnd: {}'.format(patEnd)
    
    ## search the beginning tag from lineStIdx, 'taglineSt' is where the beginning tag is found    
    while (taglineSt+taglineRange < lineStIdx+lineLtd):
        if re.search(patBegin,datalines[taglineSt]):
            #print ('taglineSt: {}'.format(taglineSt))
            taglineRange = 1
            ## when the beginning tag is found, (taglineSt is set), search the ending tag istead
            ## loop terminates when ending tag is found
            while not(re.search(patEnd,datalines[taglineSt+taglineRange])):
                ## error happens when the ending tag is not found but the beginning tag
                if re.search(patBegin,datalines[taglineSt+taglineRange]):
                    return [0, 0]    ## found another beginning before ending tag
                ##  ending tag is not found, keep searching next line by increasing taglineRange
                taglineRange += 1
                ## error happens when the searching range reaches the specified limited 
                #if taglineSt+taglineRange >=len(datalines):
                if taglineRange >= lineLtd- (taglineSt - lineStIdx):
                    #print ('ending not found {}'.format(taglineRange))
                    return [0, -1]
            #print datalines[taglineSt+taglineRange]
            break  ## pair tag match  
        else:
            ## beginning tag not found, keep searching by increasing taglineSt
            taglineSt +=1
    
    ## error happens when the searching range reaches the specified limited 
    if taglineSt >= (lineStIdx+lineLtd):
        #print '<{}> Not found'.format(tagStr)
        taglineRange = 1
        ## check if ending tag is found within the range
        while not(re.search(patEnd,datalines[lineStIdx+taglineRange])):
            taglineRange += 1
            ## not found the ending tag
            if taglineRange >= lineLtd:
                ## return as both tag cannot be found within the search range
                return [0, taglineSt - lineStIdx]
        ## error: beginnin tag not found but ending tag found 
        return [-1, taglineSt - lineStIdx]
    
    ## tag found with beginning and ending in pairs
    return [taglineSt, taglineRange]






#-------------------------------------------------------------------------------   
#   get_data_amount()
#   get the value of the specified tagname
#   return the range of the tagname, the value in float, updated lineNo, updated lineRange
#-------------------------------------------------------------------------------   
def get_data_amount(datalines, dataTagName, lineNo, lineRange):
    dataAMount = 0
    dataTagRange = parse_pairTag(datalines,lineNo,lineRange,dataTagName)
    
    ## find the locations of the given dataTagName pairs, result stored in dataTagRange
    if (dataTagRange[0]>0):
        ## get the value within the tag
        dataAMount = parse_Tag2Value(datalines, dataTagRange[0]+1, dataTagRange[1]-1)
        ## only non-negative value is acceptable
        if (dataAMount>=0):
            ## renew lineRange and lineNo for next use
            lineRange -= dataTagRange[0] - lineNo + dataTagRange[1]
            lineNo = dataTagRange[0] +  dataTagRange[1] + 1
        else:
            dataAMount = 0    ## data contain error, either <char> error, or data beginning without $
            
    return dataTagRange, dataAMount, lineNo, lineRange            





#-------------------------------------------------------------------------------   
#   parse_amount()
#   parse the whole given file. 
#   obtain RemainBalance amount and the valued in every existed transaction.
#   tagName pairs correctness will be checked. and the correctness of the value 
#   strings as well.    
#-------------------------------------------------------------------------------   
def parse_amount(path, fname):
    
    lineNo = 0
    transNo = 0
    leftAmount = 0.0
    depositAmount = 0.0
    withdrawalAmount = 0.0
    balanceAmount = 0.0
    
    with open(join(path, fname)) as f:
        datalines = [fx.strip() for fx in list(f)]
        ## replace space before or after '='
        datalines = [re.sub(' =','=', fx) for fx in datalines]
        datalines = [re.sub('= ','=', fx) for fx in datalines]
        while (lineNo < len(datalines)):
            ## get RemainBalance value and related parameters            
            RemainBalanceTagResult, leftAmount, lineNo, transRowsLeft = \
                get_data_amount(datalines, 'RemainBalanceField', lineNo, len(datalines))

            if ((RemainBalanceTagResult[0] < 1) or (RemainBalanceTagResult[1] < 1)):
                return ("RemainBalance tag error.")
            
            ## looping to find transaction entries 
            while (lineNo < len(datalines)):
                TransactionRecordTagResult = parse_pairTag(datalines,lineNo, transRowsLeft,'TransactionRecordRow')
                                
                if (TransactionRecordTagResult[0]>0):
                    ## when legal transaction tag pair is found, get withdrawal/deposit, and balance value respectively
                    #print "TransactionRecordTagResult: {}".format(TransactionRecordTagResult)
                    depositAmount = 0.0
                    withdrawalAmount = 0.0
                    balanceAmount = 0.0
                    ## set the searching boundary as the range of rows of this transaction
                    transRowsLeft = TransactionRecordTagResult[1]
                    ## examine the correctness of the transaction index
                    #print ('TransactionRecordRow Tag, {}, {} '.format(TransactionRecordTagResult[0],TransactionRecordTagResult[1]))
                    tmp = re.search(r"index=\"(\d+)\"", datalines[TransactionRecordTagResult[0]])
                    if tmp and (int(tmp.group(1)) == transNo+1):
                        transNo +=1
                    else:
                       # print datalines[TransactionRecordTagResult[0]]
                        return ("Transaction index error. Expecting {}, found data {}".format(transNo+1, datalines[TransactionRecordTagResult[0]]))
                    ## start to find the value from next line of the location of transaction tag 
                    lineNo = TransactionRecordTagResult[0]+1
                    
                    ## get the value of withdrawal, could be null
                    #print (">>WithdrawalField transRowsLeft: {} {}".format(lineNo,transRowsLeft))  
                    withdrawalTagResult, withdrawalAmount, lineNo, transRowsLeft = get_data_amount(datalines, 'WithdrawalField', lineNo, transRowsLeft)    
                    ## when the withdrawalAmount is negative, it means something wrong with the value string
                    if (withdrawalTagResult[0] == -1) or (withdrawalTagResult[1] == -1):
                        return 'WithdrawalField tag pair error {}'.format(lineNo+transRowsLeft-1)
                    elif withdrawalAmount == -1:
                        return 'WithdrawalField value error {}'.format(lineNo+transRowsLeft-1)
                    
                    ## get the value of deposit, could be null
                    #print (">>DepositField transRowsLeft:{} {}".format(lineNo,transRowsLeft))        
                    depositTagResult, depositAmount, lineNo, transRowsLeft = get_data_amount(datalines, 'DepositField', lineNo, transRowsLeft)    
                    ## when the depositAmount is negative, it means something wrong with the value string
                    if (depositTagResult[0] == -1) or (depositTagResult[1] == -1):
                        return 'DepositField tag pair error {}'.format(lineNo+transRowsLeft-1)
                    elif depositAmount == -1:
                        return 'DepositField value error {}'.format(lineNo+transRowsLeft-1)
 
                    ## get the value of balance
                    #print (">>BalanceField transRowsLeft:{} {}".format(lineNo,transRowsLeft))
                    balanceTagResult, balanceAmount, lineNo, transRowsLeft = get_data_amount(datalines, 'BalanceField', lineNo, transRowsLeft)    
                    ## when the balanceAmount is negative, it means something wrong with the value string
                    if (balanceTagResult[0] == -1) or (balanceTagResult[1] == -1):
                        return 'BalanceField tag pair error {}'.format(lineNo+transRowsLeft-1)
                    elif balanceAmount == -1:
                        return 'BalanceField value error {}'.format(lineNo+transRowsLeft-1)

                    ## either deposit or withdrawal must be found, and balance cannot be null,
                    ## or any of the ending tag must not exceed the boundary of this transaction,
                    ## otherwise, it is a transaction error. 
                    if ((depositTagResult[0]==0 or withdrawalTagResult==0) and balanceTagResult[0]==0) or \
                       ( depositTagResult[1]>TransactionRecordTagResult[1] or \
                         withdrawalTagResult[1]>TransactionRecordTagResult[1] or \
                         balanceTagResult[1]>TransactionRecordTagResult[1]): 
                        return 'Transaction No.{}: contain or sequence error'.format(transNo)

                    ## either of which must have value
                    if (depositAmount==0 and withdrawalAmount==0):
                        return 'Transaction No.{}: Deposit or Withdrawal value error'.format(transNo)

                    ## examine value logical correctness
                    if (leftAmount + depositAmount - withdrawalAmount != balanceAmount):
                        if (depositAmount):
                            return 'Transaction No.{} data error: ${:,.2f} + ${:,.2f}!=${:,.2f}'\
                            .format(transNo, leftAmount, depositAmount, balanceAmount)
                        else:   ## withdrawal case
                            return 'Transaction No.{} data error: ${:,.2f}- ${:,.2f}!=${:,.2f}'\
                            .format(transNo, leftAmount, withdrawalAmount, balanceAmount)
                    else:
                        ## one transaction examine pass
                        leftAmount = balanceAmount
                        lineNo = TransactionRecordTagResult[0] + TransactionRecordTagResult[1]+1
                        transRowsLeft = len(datalines) - lineNo
                        #print ("leftAmount: {}".format(leftAmount))
                        #print "pass trans {}\n".format(transNo)
                elif (TransactionRecordTagResult[0]<0):
                    return 'Transaction pair error (beginning not found) after transNo {}'.format(transNo)
                ## if transaction ending tag not found, but another transaction beginning is found  
                elif  (TransactionRecordTagResult[1]==0):
                   return 'Transaction pair error (illegal beginning found instead of ending) at transNo {}'.format(transNo+1)#+transRowsLeft-1)
                ## keep searching next line to get 
                elif (TransactionRecordTagResult[1]==-1):
                    return 'Transaction pair error (ending not found) at transNo {}'.format(transNo+1)#+transRowsLeft-1)
                ## when searching pointer reaches the end of the file
                elif (lineNo+TransactionRecordTagResult[1] == len(datalines)):
                    ## no more transactions can be found
                    #print lineNo, TransactionRecordTagResult[1]
                    f.close()
                    return 'Pass'
                else:
                    ## non-define status
                    return 'non-define status'
        
    return 'non-define status'





if __name__ == "__main__":

    xmlFilePath = join(getcwd(), './out/')
    
    allfiles = [f for f in listdir(xmlFilePath) if isfile(join(xmlFilePath, f))]
    
    for fname in allfiles:
        if (re.search(r'(.+).xml',fname)):
            #fname = 'CTBC_0_000001.xml'
            result = parse_amount(xmlFilePath, fname)
            print ("{}: {}".format(fname, result))
            #break
    
