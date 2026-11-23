package com.ssafy.a204.EodiLog.global.security;

import java.util.UUID;

// Verified principal, without token material or personal information.
public record AuthUser(UUID userId) {
}
