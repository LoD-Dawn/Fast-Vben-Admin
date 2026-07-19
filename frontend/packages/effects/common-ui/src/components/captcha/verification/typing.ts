export interface VerificationProps {
  barSize?: { height: string; width: string };
  captchaType?: 'blockPuzzle' | 'clickWord';
  explain?: string;
  imgSize?: { height: string; width: string };
  mode?: 'fixed' | 'pop';
  checkCaptchaApi?: (data: any) => Promise<any>;
  getCaptchaApi?: (data: any) => Promise<any>;
}
