
import React, { useState, useEffect } from 'react';
import ProductList from './components/ProductList';
import CartPage from './components/CartPage';
import { CartProvider, useCart } from './contexts/CartContext';
import { useTelegram } from './hooks/useTelegram';
import { mockProducts } from './constants';
import { Product } from './types';
import FloatingCartButton from './components/FloatingCartButton';

type View = 'products' | 'cart';

const AppContent: React.FC = () => {
    const [view, setView] = useState<View>('products');
    const { tg, colorScheme } = useTelegram();
    const { addToCart, cartItems } = useCart();
    
    useEffect(() => {
        tg.ready();
    }, [tg]);

    useEffect(() => {
        if (colorScheme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    }, [colorScheme]);
    
    useEffect(() => {
        // Handle pre-populating cart from bot's start_param
        const startParam = tg.initDataUnsafe?.start_param;
        if (startParam) {
            const productIds = startParam.split(',').map(id => parseInt(id.trim(), 10));
            const productsToAdd = mockProducts.filter(p => productIds.includes(p.id));
            productsToAdd.forEach(product => {
                if (product.status === 'in_stock') {
                    addToCart(product);
                }
            });
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tg.initDataUnsafe?.start_param]);

    return (
        <div className="bg-background text-text min-h-screen font-sans">
            <div className="max-w-4xl mx-auto pb-24">
                {view === 'products' && <ProductList products={mockProducts} />}
                {view === 'cart' && <CartPage setView={setView} />}
            </div>
            {view === 'products' && cartItems.size > 0 && <FloatingCartButton setView={setView} />}
        </div>
    );
}


const App: React.FC = () => {
    return (
        <CartProvider>
            <AppContent />
        </CartProvider>
    );
};


export default App;
