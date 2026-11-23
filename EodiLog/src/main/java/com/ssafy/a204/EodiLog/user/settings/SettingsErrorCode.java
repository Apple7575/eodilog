package com.ssafy.a204.EodiLog.user.settings;

import com.ssafy.a204.EodiLog.global.common.error.ErrorCode;
import org.springframework.http.HttpStatus;

public enum SettingsErrorCode implements ErrorCode {
    VERSION_CONFLICT;

    @Override public HttpStatus status() { return HttpStatus.CONFLICT; }
    @Override public String code() { return name(); }
    @Override public String message() { return "설정이 변경되었습니다. 다시 조회해 주세요."; }
}
