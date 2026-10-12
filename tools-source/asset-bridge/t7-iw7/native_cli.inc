		// Dedicated, exact target: never fall through to the old T7-only parser.
		if (utils::flags::has_flag("t7-iw7-model"))
		{
			try
			{
				int wide_count = 0;
				auto wide_args = CommandLineToArgvW(GetCommandLineW(), &wide_count);
				if (!wide_args) throw std::runtime_error("Could not inspect exact export arguments");
				const auto free_args = gsl::finally([&] { LocalFree(wide_args); });
				if (wide_count != 5) throw std::runtime_error("Exactly four export arguments required");
				for (int a = 1; a < wide_count; ++a)
					for (const wchar_t* p = wide_args[a]; *p; ++p)
						if (*p < 0x20 || *p > 0x7e) throw std::runtime_error("ASCII export arguments required");
				if (args.size() != 5 || args[1] != "-t7-iw7-model")
					throw std::runtime_error("usage: -t7-iw7-model <zone> <exact-model-name> <lod 0..5>");
				export_resident_model_iw7(args[2], args[3], args[4]);
				std::fflush(nullptr);
				std::quick_exit(EXIT_SUCCESS);
			}
			catch (const std::exception& error)
			{
				ZONETOOL_ERROR("T7 resident IW7 export refused: %s", error.what());
				std::fflush(nullptr);
				std::quick_exit(EXIT_FAILURE);
			}
		}
