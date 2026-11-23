package com.ssafy.a204.EodiLog.place.provider;

import java.util.List;

/** last가 true면 공급자에게 더 받을 결과가 없다. */
public record ProviderPage(List<ProviderPlace> places, boolean last) {
}
