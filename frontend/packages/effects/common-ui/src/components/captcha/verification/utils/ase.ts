import CryptoJS from 'crypto-js';

export function aesEncrypt(value: string, secretKey: string) {
  return CryptoJS.AES.encrypt(
    value,
    CryptoJS.enc.Utf8.parse(secretKey),
    {
      mode: CryptoJS.mode.ECB,
      padding: CryptoJS.pad.Pkcs7,
    },
  ).toString();
}

export function aesDecrypt(value: string, secretKey: string) {
  return CryptoJS.AES.decrypt(
    value,
    CryptoJS.enc.Utf8.parse(secretKey),
    {
      mode: CryptoJS.mode.ECB,
      padding: CryptoJS.pad.Pkcs7,
    },
  ).toString(CryptoJS.enc.Utf8);
}
