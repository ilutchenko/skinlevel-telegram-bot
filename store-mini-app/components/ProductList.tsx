
import React, { useMemo } from 'react';
import { Product } from '../types';
import ProductItem from './ProductItem';

interface ProductListProps {
    products: Product[];
}

const ProductList: React.FC<ProductListProps> = ({ products }) => {
    const groupedProducts = useMemo(() => {
        return products
            .filter(p => p.status !== 'hidden')
            .reduce((acc, product) => {
                (acc[product.category] = acc[product.category] || []).push(product);
                return acc;
            }, {} as Record<string, Product[]>);
    }, [products]);

    const categories = Object.keys(groupedProducts);

    return (
        <div>
            <header className="p-4 text-center">
                <h1 className="text-3xl font-bold text-text dark:text-gray-100">Наша коллекция</h1>
                <p className="text-hint mt-1">Откройте премиальную косметику специально для вас</p>
            </header>
            <div className="flex flex-col">
                {categories.map(category => (
                    <div key={category} className="relative">
                        <h2 className="sticky top-0 bg-background dark:bg-gray-800 bg-opacity-90 dark:bg-opacity-90 backdrop-blur-sm p-4 text-2xl font-bold text-text z-10 shadow-sm">
                            {category}
                        </h2>
                        <div className="p-2 sm:p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                            {groupedProducts[category].map(product => (
                                <ProductItem key={product.id} product={product} />
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ProductList;
