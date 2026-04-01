def main():
    from invoicing.utils.autosync_scheduler import schedule_autosync

    schedule_autosync()


if __name__ == "__main__":
    import django

    django.setup()
    main()
