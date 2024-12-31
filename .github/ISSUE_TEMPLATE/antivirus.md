---
name: Antiviral false positive or Trojan detection
about: Any flavour of reports from antivirus software regarding either PyInstaller's bootloaders or software built by PyInstaller.
title: 'Not here! Click "Preview" below for what to do instead.'
labels: antivirus-false-positives, 'solution:invalid'
assignees: ''

---

This is <u>**NOT**</u> the place for any kind of antivirus (AV) reports. Any such issues raised here will be closed either with a terse and probably sarcastic comment or no comment at all as there really is nothing we can do. False positives should instead be reported to the vendors of the offending antivirus software.

Antiviral false positives are a common theme in distributing software. Python is usually exempt from this because most antiviral software doesn't understand that Python code is still code and is therefore dangerous but, now that you're entering executable territory, you're also leaving behind the happy little AV free bubble that interpreted languages live in.

Contrary to popular expectation, there is no magic `--i-am-not-malware` option <sup>well there is one on Windows (#5579) but it's set already. If you happen to find another then go ahead and raise a feature request.</sup> so please don't expect one from us. Distribution tools like PyInstaller will have malware authors amongst its user base and as a result, *machine learning*  (which in this case just means heuristics) based antiviral software respond by blocking anything PyInstaller. This means that, if we change something to improve antivirus detections, the malicious code will change too, the heuristics will adapt to the new malicious code and anything PyInstaller will become blocked again. This is an indefinite cycle and is why nothing can be done to change PyInstaller.


### Reporting false positives to AV vendors

Instead of randomly changing your code or PyInstaller configuration in the hope that AV likes it better that way, most, if not all, antiviral software vendors should have a false positives submission portal where you can upload either your compiled binaries. For convenience, a quick list of shame for the more error-prone vendors is given below. For a more extensive list, see [this page](https://www.techsupportalert.com/how-to-report-malware-or-false-positives-to-multiple-antivirus-vendors/).

* [Microsoft Defender](https://www.microsoft.com/wdsi/filesubmission) (previously called *Windows Defender*)
* [MacAfee](https://www.microsoft.com/en-us/wdsi/filesubmission) (requires a paid *corporate* account to submit files)
* [AVG](https://www.avg.com/en-us/false-positive-file-form)
* [Qihoo-360](http://www.360totalsecurity.com/en/suspicion.html)
* [Zillya](mailto:antivirus@zillya.com?subject=False%20Positive%20Submission&body=The%20sample%20is%20in%20a%20password%20protected%20zip%20file%0A%0AThe%20password%20for%20the%20attachment%20is%20infected) (via email only)


### How do we know that our compiler chain (and therefore the bootloaders) really aren't infected?

You can never know for sure if an executable is trustworthy but we have recompiled our bootloaders plenty of times on different machines giving bit for bit (or [as close as MSVC lets you get](https://bytepointer.com/articles/the_microsoft_rich_header.htm)) reproducibility. So unless they are all identically infected then this can't be it.

On the other hand, we have seen through repeatedly submitting the same files for analysis at intervals that the results are far even from being consistent which puts their accuracy under serious question. We've also observed that it's not until a few days after a new release that antiviruses suddenly decide that our bootloaders are malicious.

Some of classifications we receive (such as an *Artemis*) aren't even based on the behaviour of a program but on the rate at which it goes from having never been seen before to being seen across many devices (its *going viral*). Imagine how this *viral* detection would play out when a new PyInstaller version gets released and 25,000 Windows users download it from PyPI each day, build applications with it, then distribute those applications to yet more people.

If you're still not convinced then audit the [source code](https://github.com/pyinstaller/pyinstaller/tree/develop/bootloader/src) and [build the bootloaders](https://pyinstaller.readthedocs.io/en/latest/bootloader-building.html) yourself.


### How can so many antiviruses think its malware simultaneously and all be wrong?

Many antiviruses are connected to the *Global Threat Intelligence Database* which is a highly marketable way for different antivirus vendors to quickly share their classifications. Whilst this sounds great in theory, in practice it means that if one antivirus mistakenly thinks that PyInstaller is malware, it'll upload misleading information to this database so that many other vendors will then parrot the same incorrect results.


### Some prior version of PyInstaller has significantly fewer antivirus detections. Doesn't that make it a regression in PyInstaller?

No, most antiviruses do not read code. Instead they memorise parts of files and hope that the parts of the files they are memorising really are the parts that make said files either malicious or not. If one version of PyInstaller receives less false positives than another it is **not** an indication that the first version was doing something right and the other was doing something wrong – it's just that they are different, have different checksums and therefore need to be memorised all over again. We can achieve similar dramatic changes in detection rates by making benign changes to our bootloaders such as changing the C compiler version or even passing `.c` files to the compiler in a different order.


# Using `-w/--windowed` mode cause a higher detection rate. Is that a bug?

No, it's just a reflection of the fact that most people distributing malware using PyInstaller will be using windowed mode.


### What can you do to get it to run on your computer?

* The preferred way is to disable your antivirus. Now that you know how it works, you also know that it doesn't work and that all along it was just giving you a false sense of security.
* Replace your antivirus with a better one (preferably one that doesn't use AI or the Global Threat Intelligence Database).


### What can you do to get it working for users?

* [Reporting false positives to AV vendors](#reporting-false-positives-to-av-vendors) is the correct way and some providers even provide APIs to do so automatically. They should eventually whitelist your software as OK. Bear in mind that users will likely need to first install some form of security update for that whitelist to propagate to their own computer before they stop seeing warnings.
* [Recompiling the bootloaders](https://pyinstaller.readthedocs.io/en/latest/bootloader-building.html) yourself can make applications better accepted by the heuristics based AVs just because it makes yours different. In particular, use gcc instead of the MSVC compiler on Windows to differentiate yourself even more from the norm. Note that this is a double edged sword however - by being different your application will not benefit if PyInstaller's bootloaders get whitelisted. Also be aware that if enough people do this, the heuristics will swing the other way and you're back to square one again.
* Tell your users to follow the steps [above](#what-can-you-do-to-get-it-to-run-on-your-computer).
* Purchase [codesign certificate](https://www.digicert.com/signing/code-signing-certificates) for few hundred dollars a year. Note that this is not guaranteed to fix AV false positives but it should make them less common. Feedback wanted on to what extent this helps from people who've tried it.


### This is not good enough. Why is there no proper solution?

Because we have no control over other organisations' broken antivirus software. Believe me, I'm just as frustrated and unable to do anything about it as you are.
