import 'package:flutter/widgets.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

enum AppFormFactor { phone, compactTablet, fullTablet }

extension AppFormFactorX on AppFormFactor {
  bool get isTablet => this != AppFormFactor.phone;
  bool get isFullTablet => this == AppFormFactor.fullTablet;
}

AppFormFactor formFactorForWidth(double width) {
  if (width < AppBreakpoints.phoneMax) {
    return AppFormFactor.phone;
  }
  if (width < AppBreakpoints.compactTabletMax) {
    return AppFormFactor.compactTablet;
  }
  return AppFormFactor.fullTablet;
}

AppFormFactor formFactorOf(BuildContext context) {
  return formFactorForWidth(MediaQuery.sizeOf(context).width);
}
