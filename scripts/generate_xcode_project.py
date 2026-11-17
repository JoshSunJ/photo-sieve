#!/usr/bin/env python3
"""Generate a small, deterministic Xcode project without requiring XcodeGen."""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "ios"


def uid(name):
    return hashlib.sha256(name.encode()).hexdigest()[:24].upper()


def main():
    sources = sorted((ROOT / "PhotoSieve").glob("*.swift"))
    objects = []

    def obj(name, body):
        objects.append(f"\t\t{uid(name)} = {{ {body} }};")

    source_refs, build_refs = [], []
    for source in sources:
        ref, build = uid(source.name), uid("build:" + source.name)
        source_refs.append(ref)
        build_refs.append(build)
        obj(source.name, f'isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = "{source.name}"; sourceTree = "<group>";')
        obj("build:" + source.name, f"isa = PBXBuildFile; fileRef = {ref};")
    obj("Info.plist", 'isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>";')
    obj("app", 'isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = PhotoSieve.app; sourceTree = BUILT_PRODUCTS_DIR;')
    obj("sourcesGroup", f'isa = PBXGroup; children = ({", ".join(source_refs + [uid("Info.plist")])}); path = PhotoSieve; sourceTree = "<group>";')
    obj("products", f'isa = PBXGroup; children = ({uid("app")}); name = Products; sourceTree = "<group>";')
    obj("mainGroup", f'isa = PBXGroup; children = ({uid("sourcesGroup")}, {uid("products")}); sourceTree = "<group>";')
    obj("sources", f'isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = ({", ".join(build_refs)}); runOnlyForDeploymentPostprocessing = 0;')
    obj("frameworks", 'isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0;')
    obj("resources", 'isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0;')
    for config in ["Debug", "Release"]:
        project_settings = 'CLANG_ENABLE_MODULES = YES; SDKROOT = iphoneos; IPHONEOS_DEPLOYMENT_TARGET = 17.0; SWIFT_VERSION = 5.0;'
        target_settings = ('CODE_SIGN_STYLE = Automatic; GENERATE_INFOPLIST_FILE = NO; '
                           'INFOPLIST_FILE = PhotoSieve/Info.plist; '
                           'PRODUCT_BUNDLE_IDENTIFIER = com.joshuasun.photosieve; '
                           'PRODUCT_NAME = "$(TARGET_NAME)"; TARGETED_DEVICE_FAMILY = 1; '
                           'SUPPORTED_PLATFORMS = "iphoneos iphonesimulator"; '
                           'LD_RUNPATH_SEARCH_PATHS = "$(inherited) @executable_path/Frameworks"; '
                           'SWIFT_STRICT_CONCURRENCY = minimal;')
        if config == "Debug":
            target_settings += ' SWIFT_OPTIMIZATION_LEVEL = "-Onone"; SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;'
        else:
            target_settings += ' SWIFT_OPTIMIZATION_LEVEL = "-O"; SWIFT_COMPILATION_MODE = wholemodule;'
        obj("project" + config, f'isa = XCBuildConfiguration; buildSettings = {{ {project_settings} }}; name = {config};')
        obj("target" + config, f'isa = XCBuildConfiguration; buildSettings = {{ {target_settings} }}; name = {config};')
    for kind in ["project", "target"]:
        obj(kind + "Configs", f'isa = XCConfigurationList; buildConfigurations = ({uid(kind + "Debug")}, {uid(kind + "Release")}); defaultConfigurationIsVisible = 0; defaultConfigurationName = Release;')
    obj("target", f'isa = PBXNativeTarget; buildConfigurationList = {uid("targetConfigs")}; buildPhases = ({uid("sources")}, {uid("frameworks")}, {uid("resources")}); buildRules = (); dependencies = (); name = PhotoSieve; productName = PhotoSieve; productReference = {uid("app")}; productType = "com.apple.product-type.application";')
    obj("project", f'isa = PBXProject; attributes = {{ LastUpgradeCheck = 1600; }}; buildConfigurationList = {uid("projectConfigs")}; compatibilityVersion = "Xcode 14.0"; developmentRegion = en; hasScannedForEncodings = 0; knownRegions = (en, Base); mainGroup = {uid("mainGroup")}; productRefGroup = {uid("products")}; projectDirPath = ""; projectRoot = ""; targets = ({uid("target")});')
    project = ROOT / "PhotoSieve.xcodeproj"
    project.mkdir(exist_ok=True)
    text = '// !$*UTF8*$!\n{\n\tarchiveVersion = 1;\n\tclasses = {};\n\tobjectVersion = 56;\n\tobjects = {\n' + "\n".join(objects) + f'\n\t}};\n\trootObject = {uid("project")};\n}}\n'
    (project / "project.pbxproj").write_text(text)
    schemes = project / "xcshareddata" / "xcschemes"
    schemes.mkdir(parents=True, exist_ok=True)
    reference = (f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{uid("target")}" '
                 'BuildableName="PhotoSieve.app" BlueprintName="PhotoSieve" ReferencedContainer="container:PhotoSieve.xcodeproj"/>')
    scheme = ('<?xml version="1.0" encoding="UTF-8"?>\n<Scheme LastUpgradeVersion="1600" version="1.3">'
              '<BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries>'
              '<BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">'
              + reference + '</BuildActionEntry></BuildActionEntries></BuildAction>'
              '<LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" '
              'selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" '
              'ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" debugServiceExtension="internal" allowLocationSimulation="YES">'
              '<BuildableProductRunnable runnableDebuggingMode="0">' + reference + '</BuildableProductRunnable></LaunchAction>'
              '<ProfileAction buildConfiguration="Release" shouldUseLaunchSchemeArgsEnv="YES" savedToolIdentifier="" useCustomWorkingDirectory="NO" debugDocumentVersioning="YES">'
              '<BuildableProductRunnable runnableDebuggingMode="0">' + reference + '</BuildableProductRunnable></ProfileAction>'
              '<AnalyzeAction buildConfiguration="Debug"/><ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES"/></Scheme>')
    (schemes / "PhotoSieve.xcscheme").write_text(scheme)
    print(project)


if __name__ == "__main__":
    main()
