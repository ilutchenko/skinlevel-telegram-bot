
import { useMemo } from 'react';

// FIX: Add Telegram to the Window interface to avoid TypeScript errors.
declare global {
    interface Window {
        Telegram: any;
    }
}

const tg = window.Telegram.WebApp;

export function useTelegram() {
    const onClose = () => {
        tg.close();
    };

    const onToggleButton = () => {
        if (tg.MainButton.isVisible) {
            tg.MainButton.hide();
        } else {
            tg.MainButton.show();
        }
    };
    
    // Using useMemo to prevent re-creating the object on every render
    const value = useMemo(() => {
        return {
            onClose,
            onToggleButton,
            tg,
            user: tg.initDataUnsafe?.user,
            queryId: tg.initDataUnsafe?.query_id,
            colorScheme: tg.colorScheme,
            initDataUnsafe: tg.initDataUnsafe,
        };
    }, []);

    return value;
}
