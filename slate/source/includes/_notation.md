# Notaion

## Sender Address

使用者的錢包地址。

The address from user

一個使用者通常會擁有:

* 錢包地址

    用來發布合約、匯款等等的在vChain上的活動。

* 地址公鑰
* 地址私鑰
* VM地址

    在VM環境下，使用者地址或是合約地址都會被轉成VM地址來讓VM辨識。

## Multisig Address

合約的多簽地址，一個多簽地址會存在多個合約地址。

e.g. 多簽地址：[合約地址A, 合約地址B, ...]

ps 在多簽地址的state file中，這些合約地址會使用VM地址來儲存。

## Contract Address

合約地址，包含合約原始碼以及此合約的資料。

