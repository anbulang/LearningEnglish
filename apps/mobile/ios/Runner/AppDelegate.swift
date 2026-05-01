import Flutter
import Network
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  private var localNetworkBrowser: NWBrowser?

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    triggerLocalNetworkPermissionPrompt()
    DispatchQueue.main.asyncAfter(deadline: .now() + 1) { [weak self] in
      self?.triggerNetworkPermissionPreflight()
    }
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
  }

  private func triggerNetworkPermissionPreflight() {
    guard
      let value = Bundle.main.object(forInfoDictionaryKey: "LearningEnglishPreflightURL") as? String,
      !value.isEmpty,
      !value.contains("$("),
      let url = URL(string: value)
    else {
      return
    }

    URLSession.shared.dataTask(with: URLRequest(url: url, timeoutInterval: 5)).resume()
  }

  private func triggerLocalNetworkPermissionPrompt() {
    let browser = NWBrowser(
      for: .bonjour(type: "_http._tcp", domain: nil),
      using: .tcp
    )
    localNetworkBrowser = browser
    browser.start(queue: .main)
  }
}
