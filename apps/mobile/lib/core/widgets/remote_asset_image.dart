import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

@visibleForTesting
bool isSvgAssetUrl(String value) {
  return Uri.tryParse(value)?.path.toLowerCase().endsWith('.svg') ??
      value.toLowerCase().endsWith('.svg');
}

class RemoteAssetImage extends StatelessWidget {
  const RemoteAssetImage({
    required this.url,
    required this.width,
    required this.height,
    this.fit = BoxFit.cover,
    this.placeholder,
    this.errorIcon = Icons.image_not_supported_outlined,
    super.key,
  });

  final String url;
  final double width;
  final double height;
  final BoxFit fit;
  final Widget? placeholder;
  final IconData errorIcon;

  @override
  Widget build(BuildContext context) {
    if (url.trim().isEmpty) {
      return _fallback(errorIcon);
    }
    if (isSvgAssetUrl(url)) {
      return SvgPicture.network(
        url,
        width: width,
        height: height,
        fit: fit,
        placeholderBuilder: (context) =>
            placeholder ?? _fallback(Icons.image_outlined),
        errorBuilder: (context, error, stackTrace) => _fallback(errorIcon),
      );
    }
    return Image.network(
      url,
      width: width,
      height: height,
      fit: fit,
      errorBuilder: (context, error, stackTrace) => _fallback(errorIcon),
    );
  }

  Widget _fallback(IconData icon) {
    return Container(
      width: width,
      height: height,
      color: AppColors.paperWhite,
      alignment: Alignment.center,
      child: Icon(icon),
    );
  }
}
