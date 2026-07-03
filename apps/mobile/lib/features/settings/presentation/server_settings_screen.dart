import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:learning_english_design_tokens/design_tokens.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/server_config.dart';
import '../../../core/widgets/app_card.dart';
import '../../session/data/session_controller.dart';

/// Lets an internal tester repoint the app at a different backend without a
/// recompile. The override is persisted by [ServerConfig] and applied to the
/// live [ApiClient] immediately.
class ServerSettingsScreen extends ConsumerStatefulWidget {
  const ServerSettingsScreen({super.key});

  @override
  ConsumerState<ServerSettingsScreen> createState() =>
      _ServerSettingsScreenState();
}

class _ServerSettingsScreenState extends ConsumerState<ServerSettingsScreen> {
  late final TextEditingController _controller;
  String? _error;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _controller =
        TextEditingController(text: ref.read(apiClientProvider).baseUrl);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final value = _controller.text.trim();
    if (!ServerConfig.isValidBaseUrl(value)) {
      setState(() => _error = '请输入完整的服务器地址，例如 https://api.example.com/v1');
      return;
    }
    final previous = ref.read(apiClientProvider).baseUrl;
    setState(() {
      _error = null;
      _saving = true;
    });
    await ref.read(serverConfigProvider).saveOverride(value);
    ref.read(apiClientProvider).baseUrl = value;
    // Tokens belong to the previous backend — drop the session so the app forces
    // a clean re-login instead of sending stale tokens (which 401) to the new one.
    if (value != previous) {
      await ref.read(sessionControllerProvider.notifier).clearSession();
    }
    if (!mounted) {
      return;
    }
    setState(() => _saving = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('服务器地址已保存，请重新登录后生效。')),
    );
    if (context.canPop()) {
      context.pop();
    }
  }

  Future<void> _resetToDefault() async {
    final previous = ref.read(apiClientProvider).baseUrl;
    setState(() {
      _error = null;
      _saving = true;
    });
    await ref.read(serverConfigProvider).clearOverride();
    ref.read(apiClientProvider).baseUrl = ApiClient.defaultBaseUrl;
    // Repointing to a different backend invalidates the current session's tokens.
    if (previous != ApiClient.defaultBaseUrl) {
      await ref.read(sessionControllerProvider.notifier).clearSession();
    }
    if (!mounted) {
      return;
    }
    setState(() {
      _saving = false;
      _controller.text = ApiClient.defaultBaseUrl;
    });
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('已恢复为默认服务器地址。')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('服务器地址')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.md),
        children: <Widget>[
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('后端服务器地址', style: AppTextStyles.sectionTitle),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  '指向运营方提供的后端地址（需包含 /v1）。修改后请重新登录。',
                  style: AppTextStyles.helper,
                ),
                const SizedBox(height: AppSpacing.md),
                TextField(
                  controller: _controller,
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                  enableSuggestions: false,
                  decoration: InputDecoration(
                    hintText: 'https://api.example.com/v1',
                    border: const OutlineInputBorder(),
                    errorText: _error,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  '编译内置默认：${ApiClient.defaultBaseUrl}',
                  style: AppTextStyles.helper,
                ),
                const SizedBox(height: AppSpacing.md),
                Row(
                  children: <Widget>[
                    Expanded(
                      child: FilledButton.icon(
                        onPressed: _saving ? null : _save,
                        icon: const Icon(Icons.save_rounded),
                        label: const Text('保存'),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    OutlinedButton(
                      onPressed: _saving ? null : _resetToDefault,
                      child: const Text('恢复默认'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
