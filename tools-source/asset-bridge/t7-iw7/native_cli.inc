		// Dedicated, exact target: never fall through to the old T7-only parser.
		if (utils::flags::has_flag("t7-iw7-model") || utils::flags::has_flag("t7-iw7-model-v2") || utils::flags::has_flag("t7-iw7-model-streamed-v1") || utils::flags::has_flag("t7-iw7-model-streamed-v2") || utils::flags::has_flag("t7-iw7-catalog"))
		{
			try
			{
				int wide_count = 0;
				auto wide_args = CommandLineToArgvW(GetCommandLineW(), &wide_count);
				if (!wide_args) throw std::runtime_error("Could not inspect exact export arguments");
				const auto free_args = gsl::finally([&] { LocalFree(wide_args); });
				const bool catalog = args.size() == 3 && args[1] == "-t7-iw7-catalog";
				const bool streamed = args.size() == 6 && (args[1] == "-t7-iw7-model-streamed-v1" || args[1] == "-t7-iw7-model-streamed-v2");
				if (wide_count != (catalog ? 3 : streamed ? 6 : 5)) throw std::runtime_error("Exact catalogue/export argument count required");
				for (int a = 1; a < wide_count; ++a)
					for (const wchar_t* p = wide_args[a]; *p; ++p)
						if (*p < 0x20 || *p > 0x7e) throw std::runtime_error("ASCII export arguments required");
				if (catalog) catalog_resident_models_iw7(args[2]);
				else if (streamed) export_selected_streamed_model_iw7(args[2], args[3], args[4], args[5], args[1] == "-t7-iw7-model-streamed-v2");
				else if (args.size() != 5 || (args[1] != "-t7-iw7-model" && args[1] != "-t7-iw7-model-v2"))
					throw std::runtime_error("usage: -t7-iw7-model[-v2] <zone> <exact-model-name> <lod 0..5>");
				else export_resident_model_iw7(args[2], args[3], args[4], args[1] == "-t7-iw7-model-v2");
				std::fflush(nullptr);
				std::quick_exit(EXIT_SUCCESS);
			}
			catch (const std::exception& error)
			{
				if (utils::flags::has_flag("t7-iw7-model-streamed-v1") || utils::flags::has_flag("t7-iw7-model-streamed-v2"))
					ZONETOOL_ERROR("T7 selected streamed IW7 export refused: %s", error.what());
				else ZONETOOL_ERROR("T7 resident IW7 export refused: %s", error.what());
				std::fflush(nullptr);
				std::quick_exit(EXIT_FAILURE);
			}
		}
